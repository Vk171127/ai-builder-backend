"""Anomaly detector with fail-open semantics."""

from __future__ import annotations

import asyncio
from pathlib import Path

import joblib
import numpy as np

from app.models.detection import Detection
from app.schemas.feature import FeatureVector


class IsolationForestAnomalyDetector:
    def __init__(self, model_path: Path = Path("ml/models/anomaly_iforest.joblib")) -> None:
        self._model = joblib.load(model_path)

    async def detect(self, features: FeatureVector, timeout_ms: int = 50) -> Detection | None:
        async def _run() -> Detection:
            vector = np.nan_to_num(features.to_array(), nan=0.0).reshape(1, -1)
            iforest_score = float(-self._model.score_samples(vector)[0])
            amount_ratio = float(features.values.get("amount_ratio", float("nan")))
            hour_deviation = float(features.values.get("hour_deviation", float("nan")))
            payee_novelty = float(features.values.get("payee_is_new", float("nan")))

            amount_z = min(1.0, max(0.0, (0.0 if np.isnan(amount_ratio) else amount_ratio) / 5.0))
            hour_z = min(1.0, max(0.0, (0.0 if np.isnan(hour_deviation) else hour_deviation) / 12.0))
            payee_component = 0.0 if np.isnan(payee_novelty) else payee_novelty
            novelty = (0.4 * iforest_score) + (0.3 * amount_z) + (0.2 * hour_z) + (0.1 * payee_component)
            novelty = max(0.0, min(1.0, novelty))
            return Detection(detector="anomaly", score=novelty, scam_type_probs={}, evidence_event_ids=[])

        try:
            return await asyncio.wait_for(_run(), timeout=timeout_ms / 1000)
        except Exception:
            return None
