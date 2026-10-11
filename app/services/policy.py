"""Action policy mapping with hysteresis."""

from __future__ import annotations

import json

from app.models.signal import Stage
from db.state.store import StateStore

_ACTION_RANK = {"allow": 0, "nudge": 1, "warn": 2, "hold": 3}


def _base_action(risk: float, stage: Stage) -> str:
    if risk < 0.30:
        return "allow"
    if risk <= 0.60:
        return "nudge"
    if risk <= 0.85:
        return "warn"
    if stage == Stage.extraction:
        return "hold"
    return "warn"


def decide_action(
    risk: float,
    stage: Stage,
    session_id: str,
    state_store: StateStore | None,
    now_ms: int,
) -> str:
    proposed = _base_action(risk, stage)
    if state_store is None:
        return proposed

    key = f"session:{session_id}:min_action"
    raw = state_store.get(key)
    if isinstance(raw, str):
        state = json.loads(raw)
    elif isinstance(raw, dict):
        state = raw
    else:
        state = {"action": "allow", "locked_until_ms": 0}

    locked_until = int(state.get("locked_until_ms", 0))
    current = str(state.get("action", "allow"))

    if now_ms < locked_until and _ACTION_RANK.get(proposed, 0) < _ACTION_RANK.get(current, 0):
        proposed = current

    if _ACTION_RANK.get(proposed, 0) > _ACTION_RANK.get(current, 0):
        state = {"action": proposed, "locked_until_ms": now_ms + 300_000}
    else:
        state = {"action": current, "locked_until_ms": locked_until}

    state_store.set(key, json.dumps(state), px=300_000)
    return state["action"]
