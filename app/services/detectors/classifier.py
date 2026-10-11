"""Classifier detector over ONNX model."""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np
import onnxruntime as ort

from app.models.detection import Detection
from app.schemas.feature import FeatureVector


class OnnxClassifier:
    def __init__(self, model_path: Path = Path("ml/models/classifier.onnx")) -> None:
        self._session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self._input_name = self._session.get_inputs()[0].name

    async def detect(self, features: FeatureVector, timeout_ms: int = 50) -> Detection | None:
        async def _run() -> Detection:
            x = np.nan_to_num(features.to_array(), nan=0.0).reshape(1, -1).astype(np.float32)
            outputs = self._session.run(None, {self._input_name: x})
            payload = outputs[-1]
            probs: dict[str, float] = {}
            if isinstance(payload, list) and payload and isinstance(payload[0], dict):
                probs = {str(key): float(value) for key, value in payload[0].items()}
            else:
                arr = np.asarray(payload).reshape(-1)
                probs = {f"class_{idx}": float(value) for idx, value in enumerate(arr.tolist())}
            return Detection(
                detector="classifier",
                score=max(probs.values()) if probs else 0.0,
                scam_type_probs=probs,
                evidence_event_ids=[],
            )

        try:
            return await asyncio.wait_for(_run(), timeout=timeout_ms / 1000)
        except Exception:
            return None
