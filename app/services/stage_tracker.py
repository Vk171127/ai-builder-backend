"""Stage tracker over simple HMM-like beliefs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.models.signal import SignalEvent, Stage
from db.state.store import StateStore


@dataclass(slots=True)
class StageTrackerResult:
    top_scam_type: str
    top_stage: Stage
    probability: float
    stage_progression_velocity: float


_STAGE_ORDER = [Stage.contact, Stage.trust_building, Stage.isolation, Stage.pressure, Stage.extraction]


def _stage_from_behaviour(event: SignalEvent) -> Stage:
    name = event.behaviour.value if event.behaviour is not None else ""
    if name in {"normal", "suspicious", "malicious"}:
        return Stage.contact
    if name in {"AUTHORITY_CLAIM", "KEYWORD_AUTHORITY", "KEYWORD_COURIER_DRUGS", "LOOKALIKE_DOMAIN", "HOMOGLYPH_DOMAIN"}:
        return Stage.contact
    if name in {"SCREEN_SHARE_LIKELY", "SECOND_VOICE", "CARD_OTP_FORM", "KEYWORD_INVESTMENT_RETURNS"}:
        return Stage.trust_building
    if name in {"ISOLATION_DEMAND", "UNKNOWN_DEVICE", "REMOTE_ACCESS_TOOL_OPEN"}:
        return Stage.isolation
    if name in {"PASTE_OTP", "OTP_TOO_FAST", "PASTE_PAYEE"}:
        return Stage.pressure
    return Stage.contact


def update_belief(
    session_id: str,
    new_events: list[SignalEvent],
    state_store: StateStore | None,
) -> StageTrackerResult:
    if state_store is None:
        stage = _stage_from_behaviour(new_events[-1]) if new_events else Stage.contact
        return StageTrackerResult("benign", stage, 0.5, 0.0)

    belief_key = f"session:{session_id}:belief"
    applied_key = f"session:{session_id}:belief_applied"

    raw = state_store.get(belief_key)
    if isinstance(raw, str):
        belief = json.loads(raw)
    else:
        belief = {stage.value: 1.0 / len(_STAGE_ORDER) for stage in _STAGE_ORDER}

    ordered = sorted(new_events, key=lambda event: event.timestamp_ms)
    first_ts = ordered[0].timestamp_ms if ordered else 0
    last_ts = ordered[-1].timestamp_ms if ordered else first_ts

    for event in ordered:
        if state_store.sismember(applied_key, event.event_id):
            continue

        mapped = _stage_from_behaviour(event)
        trust = float(event.trust or 0.0)

        # transition/update
        for stage in _STAGE_ORDER:
            belief[stage.value] = belief.get(stage.value, 0.0) * 0.82
        belief[mapped.value] = belief.get(mapped.value, 0.0) + (0.18 * max(0.1, trust))

        # normalize
        total = sum(belief.values()) or 1.0
        for key in list(belief.keys()):
            belief[key] = belief[key] / total

        # no-backward constraint
        top = max(_STAGE_ORDER, key=lambda stage: belief.get(stage.value, 0.0))
        top_idx = _STAGE_ORDER.index(top)
        for idx, stage in enumerate(_STAGE_ORDER):
            if idx < top_idx:
                belief[stage.value] = 0.0

        # renormalize
        total = sum(belief.values()) or 1.0
        for key in list(belief.keys()):
            belief[key] = belief[key] / total

        state_store.sadd(applied_key, event.event_id)

    state_store.set(belief_key, json.dumps(belief), ex=3600)

    top_stage = max(_STAGE_ORDER, key=lambda stage: belief.get(stage.value, 0.0))
    velocity = 0.0
    if last_ts > first_ts:
        velocity = float(_STAGE_ORDER.index(top_stage) + 1) / ((last_ts - first_ts) / 1000.0)

    has_explicit_scam_signal = any(
        event.behaviour is not None
        and event.behaviour.value not in {"normal", "suspicious", "malicious"}
        for event in ordered
    )

    return StageTrackerResult(
        top_scam_type="digital_arrest"
        if has_explicit_scam_signal and top_stage in {Stage.isolation, Stage.pressure, Stage.extraction}
        else "benign",
        top_stage=top_stage,
        probability=float(belief.get(top_stage.value, 0.0)),
        stage_progression_velocity=velocity,
    )
