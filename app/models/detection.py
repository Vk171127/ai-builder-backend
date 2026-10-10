"""Detector-level outputs."""

from dataclasses import dataclass


@dataclass(slots=True)
class Detection:
    detector: str
    score_x100: int
    scam_type_probs_x100: dict[str, int]
