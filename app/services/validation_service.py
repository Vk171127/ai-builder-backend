"""Validation stage for incoming signal batches."""

from app.models.signal import SignalBatch


def validate_batch(batch: SignalBatch) -> SignalBatch:
    """Validate batch shape and return normalized payload.

    Placeholder for trust override and rate limiting logic.
    """
    return batch
