"""Routing logic for deciding enrichment lookups."""

from app.models.signal import SignalEvent


def decide_lookups(events: list[SignalEvent]) -> list[str]:
    _ = events
    return ["customer_profile", "recent_reports"]
