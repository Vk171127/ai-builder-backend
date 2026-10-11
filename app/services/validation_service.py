"""Validation stage for incoming signal batches."""

from __future__ import annotations

from app.models.signal import SignalBatch
from app.models.signal import RejectedEvent, SignalEvent, ValidatedBatch
from app.models.signal import Source
from db.state.store import StateStore, token_bucket


def validate_batch(raw: SignalBatch, now_ms: int, state_store: StateStore | None = None) -> ValidatedBatch:
    """Validate incoming batch according to hot-path contracts."""
    if len(raw.events) > 50:
        raise ValueError("HTTP_429: batch size exceeds 50")

    bucket_key = f"rate:{raw.session_id}"
    bucket = token_bucket(
        state_store,
        bucket_key,
        now_ms,
        limit=100,
        window_ms=60_000,
    )
    if not bucket.allowed:
        raise ValueError("HTTP_429: session rate limit exceeded")

    accepted: list[SignalEvent] = []
    rejected: list[RejectedEvent] = []
    min_ts = now_ms - 300_000

    for event in raw.events:
        if event.behaviour is None:
            rejected.append(RejectedEvent(event_id=event.event_id, reason="unknown_behaviour"))
            continue
        if event.timestamp_ms < min_ts:
            rejected.append(RejectedEvent(event_id=event.event_id, reason="timestamp_too_old"))
            continue
        if event.source not in {Source.phone, Source.extension, Source.server}:
            rejected.append(RejectedEvent(event_id=event.event_id, reason="invalid_source"))
            continue

        accepted.append(
            event.model_copy(
                update={
                    "trust": event.behaviour.default_trust,
                    "value_x100": int(round(event.behaviour.default_trust * 100)),
                }
            )
        )

    return ValidatedBatch(accepted=accepted, rejected_with_reasons=rejected)
