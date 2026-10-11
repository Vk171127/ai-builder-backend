"""Detector-level outputs."""

from dataclasses import dataclass


@dataclass(slots=True)
class Detection:
    detector: str
    score: float
    scam_type_probs: dict[str, float]
    evidence_event_ids: list[str]
