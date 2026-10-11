"""Main orchestration service for analyse requests."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from functools import lru_cache
from uuid import uuid4

from app.models.decision import Decision, Intervention
from app.models.detection import Detection
from app.schemas.analyse import AnalyseRequest
from app.core.config import settings
from app.services.detectors.anomaly import IsolationForestAnomalyDetector
from app.services.detectors.classifier import OnnxClassifier
from app.services.detectors.rules import detect_rules
from app.services.enrichment.adapters import build_adapters
from app.services.enrichment.runner import run_enrichment
from app.services.features.compute import compute
from app.services.fusion import fuse_risk
from app.services.intervention import build_intervention
from app.services.policy import decide_action
from app.services.reasoner.reasoner import run as run_reasoner
from app.services.reasoner.reasoner import _should_run_reasoner
from app.services.signal_processing import get_signal_processor
from app.services.session_service import load_session_window
from app.services.stage_tracker import update_belief
from app.services.validation_service import validate_batch
from app.models.signal import SignalBatch
from db.state.store import get_analysis_store, get_state_store


@dataclass(slots=True)
class HotPathArtifacts:
    decision: Decision
    all_events: list
    rules_detection: object
    classifier_detection: object
    anomaly_detection: object
    tracker: object
    novelty: float
    warm_path_triggered: bool
    latency_ms: int


class PipelineService:
    """Coordinates all Gatekeeper stages and returns a final decision."""

    def __init__(self) -> None:
        self.state = get_state_store(
            backend=settings.state_backend,
            project=settings.firestore_project_id or settings.gcp_project,
            database=settings.firestore_database,
            collection_prefix=settings.firestore_collection_prefix,
        )
        self.analyses = get_analysis_store(
            project=settings.firestore_project_id or settings.gcp_project,
            database=settings.firestore_database,
        )
        self.adapters = build_adapters()
        self.classifier = OnnxClassifier()
        self.anomaly = IsolationForestAnomalyDetector()
        self.signal_processor = get_signal_processor()

    @staticmethod
    def _action_rank(action: str) -> int:
        return {"allow": 0, "nudge": 1, "warn": 2, "hold": 3}.get(action, 0)

    def models_loaded(self) -> bool:
        return hasattr(self.classifier, "_session") and hasattr(self.anomaly, "_model")

    async def run_warm_path(
        self,
        *,
        decision: Decision,
        events,
        rule_result,
        classifier_result,
        stage_result,
        session_locale: str,
        novelty: float,
    ) -> None:
        try:
            reasoner_result = await run_reasoner(
                events=events,
                rule_result=rule_result,
                classifier_result=classifier_result,
                stage_result=stage_result,
                session_locale=session_locale,
                fused_risk=decision.risk,
                novelty=novelty,
                classifier_conf=classifier_result.score,
            )
            if reasoner_result is None:
                return

            reasoner_weight_max = 0.30
            try:
                import yaml

                policy = yaml.safe_load(open(settings.policy_file, "r", encoding="utf-8").read())
                if isinstance(policy, dict):
                    reasoner_weight_max = float(policy.get("reasoner_weight_max", 0.30))
            except Exception:
                pass

            boosted_risk = min(1.0, decision.risk + min(reasoner_weight_max, max(0.0, reasoner_result.scam_likelihood - decision.risk)))
            escalated_action = decide_action(
                risk=boosted_risk,
                stage=stage_result.top_stage,
                session_id=decision.session_id,
                state_store=self.state,
                now_ms=int(time.time() * 1000),
            )

            if rule_result.score > 0 and escalated_action == "allow":
                escalated_action = "warn"

            if self._action_rank(escalated_action) > self._action_rank(decision.action):
                decision.action = escalated_action
                decision.risk = boosted_risk
                decision.reasoner = None
            decision.explanation_pending = False
        except Exception:
            return

    async def run_hot_path(self, request: AnalyseRequest) -> HotPathArtifacts:
        started = int(time.time() * 1000)
        now_ms = int(time.time() * 1000)
        signal_batch = await self.signal_processor.to_signal_batch(request)
        validated = validate_batch(
            SignalBatch(session_id=request.session_id, events=signal_batch.events),
            now_ms=now_ms,
            state_store=self.state,
        )

        window_events = load_session_window(
            session_id=request.session_id,
            validated=validated,
            state_store=self.state,
            now_ms=now_ms,
        )

        enrichment = await run_enrichment(
            window_events,
            state_store=self.state,
            adapters=self.adapters,
            timeout_ms=80,
        )
        all_events = sorted(window_events + enrichment.synthetic_events, key=lambda event: event.timestamp_ms)

        context: dict[str, object] = {
            "payee_mule_score": (enrichment.values.get("mule_score") or {}).get("score"),
            "web_risk_flagged": (enrichment.values.get("web_risk") or {}).get("flagged"),
            "payee_in_graph": (enrichment.values.get("recent_reports") or {}).get("in_graph"),
            "avg_payment_minor": (enrichment.values.get("customer_profile") or {}).get("avg_payment_minor"),
            "usual_hour": (enrichment.values.get("customer_profile") or {}).get("usual_hour"),
        }
        fv = compute(all_events, context=context, config={"cross_device_window_s": 300})

        rules_task = asyncio.to_thread(detect_rules, all_events)
        classifier_task = self.classifier.detect(fv)
        anomaly_task = self.anomaly.detect(fv)
        rules_detection, classifier_detection, anomaly_detection = await asyncio.gather(
            rules_task,
            classifier_task,
            anomaly_task,
        )

        # Detectors fail open: a timeout or model error contributes no signal.
        if classifier_detection is None:
            classifier_detection = Detection(detector="classifier", score=0.0, scam_type_probs={}, evidence_event_ids=[])
        if anomaly_detection is None:
            anomaly_detection = Detection(detector="anomaly", score=0.0, scam_type_probs={}, evidence_event_ids=[])

        tracker = update_belief(request.session_id, all_events, self.state)

        graph_boost = 0.0
        reports = enrichment.values.get("recent_reports") or {}
        if isinstance(reports, dict):
            if reports.get("in_graph") is True:
                graph_boost = 0.10
            elif reports.get("distance") == 1:
                graph_boost = 0.20

        classifier_max = classifier_detection.score
        novelty = anomaly_detection.score
        risk = fuse_risk(
            rule_floor=rules_detection.score,
            classifier_max_prob=classifier_max,
            novelty=novelty,
            reasoner_likelihood=0.0,
            graph_boost=graph_boost,
            top_stage=tracker.top_stage,
            events=all_events,
        )

        mule = context.get("payee_mule_score")
        web_risk_flagged = context.get("web_risk_flagged")
        if (
            rules_detection.score <= 0.0
            and tracker.top_scam_type == "benign"
            and isinstance(mule, (int, float))
            and float(mule) <= 0.30
            and web_risk_flagged is not True
        ):
            risk = min(risk, 0.29)

        action = decide_action(
            risk=risk,
            stage=tracker.top_stage,
            session_id=request.session_id,
            state_store=self.state,
            now_ms=now_ms,
        )

        scam_type = tracker.top_scam_type
        if classifier_detection.scam_type_probs:
            scam_type = max(classifier_detection.scam_type_probs, key=classifier_detection.scam_type_probs.get)

        intervention: Intervention = build_intervention(
            action=action,
            scam_type=scam_type,
            language="en",
            state_store=self.state,
        )

        decision = Decision(
            id=str(uuid4()),
            session_id=request.session_id,
            risk=risk,
            action=action,
            scam_type=scam_type,
            stage=tracker.top_stage,
            explanation_pending=False,
            intervention=intervention,
        )

        warm_path_triggered = _should_run_reasoner(
            fused_risk=risk,
            novelty=novelty,
            classifier_conf=classifier_detection.score,
        )
        decision.explanation_pending = warm_path_triggered

        latency_ms = int(time.time() * 1000) - started

        return HotPathArtifacts(
            decision=decision,
            all_events=all_events,
            rules_detection=rules_detection,
            classifier_detection=classifier_detection,
            anomaly_detection=anomaly_detection,
            tracker=tracker,
            novelty=novelty,
            warm_path_triggered=warm_path_triggered,
            latency_ms=latency_ms,
        )

    async def run(self, request: AnalyseRequest) -> Decision:
        artifacts = await self.run_hot_path(request)
        if artifacts.warm_path_triggered:
            asyncio.create_task(
                self.run_warm_path(
                    decision=artifacts.decision,
                    events=artifacts.all_events,
                    rule_result=artifacts.rules_detection,
                    classifier_result=artifacts.classifier_detection,
                    stage_result=artifacts.tracker,
                    session_locale=request.session_locale,
                    novelty=artifacts.novelty,
                )
            )
        return artifacts.decision


@lru_cache(maxsize=1)
def get_pipeline_service() -> PipelineService:
    return PipelineService()
