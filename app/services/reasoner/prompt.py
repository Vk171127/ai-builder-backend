"""Prompt building utilities for reasoner."""

from app.models.signal import SignalEvent


def build_timeline(events: list[SignalEvent]) -> str:
    return " | ".join(f"{event.signal_type}:{event.value_x100}" for event in events)
