"""Feature vector schema contract for detectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import numpy as np


@dataclass(slots=True)
class FeatureVector:
    FEATURE_ORDER: ClassVar[list[str]] = [
        "presence_normal",
        "presence_suspicious",
        "presence_malicious",
        "trust_weighted_normal",
        "trust_weighted_suspicious",
        "trust_weighted_malicious",
        "session_duration_s",
        "burst_density",
        "authority_before_payment",
        "max_inter_event_gap_s",
        "has_cross_device_coercion",
        "cross_device_gap_s",
        "amount_ratio",
        "payee_is_new",
        "hour_deviation",
        "payee_mule_score",
        "web_risk_flagged",
        "payee_in_graph",
    ]
    VERSION: ClassVar[str] = "v1"

    values: dict[str, float]
    missing_flags: dict[str, bool]

    def to_array(self) -> np.ndarray:
        return np.asarray(
            [float(self.values.get(name, float("nan"))) for name in self.FEATURE_ORDER],
            dtype=np.float32,
        )
