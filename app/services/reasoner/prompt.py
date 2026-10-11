"""Prompt building utilities for reasoner."""

from __future__ import annotations

from app.models.signal import SignalEvent


def _escape_data(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")


def build_timeline(events: list[SignalEvent]) -> str:
    if not events:
        return "No timeline events available."

    ordered = sorted(events, key=lambda event: event.timestamp_ms)
    start = ordered[0].timestamp_ms
    lines: list[str] = []
    for event in ordered:
        delta_s = max(0, int((event.timestamp_ms - start) / 1000))
        mm = delta_s // 60
        ss = delta_s % 60
        trust = float(event.trust or 0.0)
        trust_label = "server-verified" if trust >= 0.7 else "client-reported"
        suffix = " (experimental)" if trust < 0.55 else ""
        description = event.behaviour.human_description if event.behaviour is not None else "Unknown behavior"

        remarks = event.metadata.get("remarks")
        phrase = event.metadata.get("detected_phrase")
        extra_bits: list[str] = []
        if isinstance(remarks, str) and remarks.strip():
            extra_bits.append(f"remarks=<data>{_escape_data(remarks.strip())}</data>")
        if isinstance(phrase, str) and phrase.strip():
            extra_bits.append(f"phrase=<data>{_escape_data(phrase.strip())}</data>")
        extra = f" {' '.join(extra_bits)}" if extra_bits else ""

        lines.append(
            f"T+{mm}:{ss:02d} [{event.source.value}, {trust_label}] {description}{suffix}{extra}"
        )
    return "\n".join(lines)
