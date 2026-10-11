"""Analyse endpoints."""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.analyse import AnalyseRequest, AnalyseResponse
from app.services.bigquery_adapter import get_bigquery_adapter
from app.services.pipeline_service import get_pipeline_service
from app.services.pubsub_adapter import get_pubsub_adapter

LOGGER = logging.getLogger(__name__)
router = APIRouter(tags=["Analyse"])


async def write_bigquery(payload: dict[str, object]) -> None:
    try:
        await get_bigquery_adapter().write_decision(payload)
    except Exception:
        LOGGER.exception("gcp_write_failed")


async def publish_pubsub(payload: dict[str, object]) -> None:
    try:
        await get_pubsub_adapter().publish_decision(payload)
    except Exception:
        LOGGER.exception("gcp_write_failed")


async def write_firestore_analysis(record: dict[str, object]) -> None:
    try:
        await asyncio.to_thread(
            get_pipeline_service().analyses.put_document,
            settings.firestore_analyses_collection,
            str(record["decision_id"]),
            record,
        )
    except Exception:
        LOGGER.exception("firestore_analysis_write_failed")


@router.post("/analyse", response_model=AnalyseResponse)
async def analyse(request: AnalyseRequest) -> AnalyseResponse:
    """Run the Gatekeeper decision pipeline."""
    lock_key = f"session:{request.session_id}:lock"
    lock_acquired = get_pipeline_service().state.set(lock_key, "1", ex=5, nx=True)
    if not lock_acquired:
        cached = get_pipeline_service().state.get(f"session:{request.session_id}:last_decision")
        if cached is not None:
            return AnalyseResponse(decision=cached)
        raise HTTPException(status_code=429, detail="session lock held")

    try:
        artifacts = await get_pipeline_service().run_hot_path(request)
        decision = artifacts.decision

        get_pipeline_service().state.set(f"session:{request.session_id}:last_decision", decision, ex=300)

        bq_payload: dict[str, object] = {
            "decision_id": decision.id,
            "decision": decision.model_dump(),
            "session_id": decision.session_id,
            "risk": decision.risk,
            "action": decision.action,
            "scam_type": decision.scam_type,
            "stage": decision.stage.value,
            "rule_hits": artifacts.rules_detection.evidence_event_ids,
            "classifier_probs": artifacts.classifier_detection.scam_type_probs,
            "novelty_score": artifacts.anomaly_detection.score,
            "reasoner_output": None,
            "policy_version": "v1",
            "latency_ms": artifacts.latency_ms,
            "explanation_pending": decision.explanation_pending,
        }

        analysis_record = {
            **bq_payload,
            "decision": decision.model_dump(mode="json"),
            "created_at_ms": int(time.time() * 1000),
        }
        asyncio.create_task(write_firestore_analysis(analysis_record))
        asyncio.create_task(write_bigquery(bq_payload))
        asyncio.create_task(publish_pubsub(bq_payload))

        if artifacts.warm_path_triggered:
            asyncio.create_task(
                get_pipeline_service().run_warm_path(
                    decision=decision,
                    events=artifacts.all_events,
                    rule_result=artifacts.rules_detection,
                    classifier_result=artifacts.classifier_detection,
                    stage_result=artifacts.tracker,
                    session_locale=request.session_locale,
                    novelty=artifacts.novelty,
                )
            )
    except ValueError as exc:
        if "HTTP_429" in str(exc):
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        raise
    finally:
        get_pipeline_service().state.delete(lock_key)
    return AnalyseResponse(decision=decision)


@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: str) -> dict[str, object]:
    """Read decision record with evidence trace from BigQuery adapter."""
    row = await get_bigquery_adapter().get_decision(decision_id)
    if row is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return {
        "decision_id": row.get("decision_id"),
        "session_id": row.get("session_id"),
        "rule_hits": row.get("rule_hits", []),
        "classifier_probs": row.get("classifier_probs", {}),
        "novelty_score": row.get("novelty_score"),
        "reasoner_output": row.get("reasoner_output"),
        "policy_version": row.get("policy_version"),
        "latency_ms": row.get("latency_ms"),
        "decision": row.get("decision"),
    }
