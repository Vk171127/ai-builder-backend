"""Session window persistence abstraction."""

from __future__ import annotations

import json

from app.models.signal import SignalEvent
from app.models.signal import ValidatedBatch
from db.state.store import StateStore


def load_session_window(
    session_id: str,
    validated: ValidatedBatch,
    state_store: StateStore | None,
    now_ms: int,
) -> list[SignalEvent]:
    """Read/merge/write 15-minute event window for a session."""
    incoming = validated.accepted
    if state_store is None:
        return sorted(incoming, key=lambda event: event.timestamp_ms)

    key = f"session:{session_id}:events"
    min_score = now_ms - 900_000
    try:
        existing_rows = state_store.zrangebyscore(key, min_score, now_ms)
        existing_events = [SignalEvent.model_validate_json(row) for row in existing_rows]
        merged: dict[str, SignalEvent] = {event.event_id: event for event in existing_events}
        for event in incoming:
            merged[event.event_id] = event

        ordered = sorted(merged.values(), key=lambda event: event.timestamp_ms)

        for event in ordered:
            state_store.zadd(key, {event.model_dump_json(): event.timestamp_ms})
        state_store.zremrangebyscore(key, -10**18, min_score)
        return ordered
    except Exception:
        return sorted(incoming, key=lambda event: event.timestamp_ms)
