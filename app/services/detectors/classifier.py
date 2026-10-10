"""Classifier detector stub (LightGBM ONNX inference)."""

from app.schemas.feature import FeatureVector


def score_classifier(features: FeatureVector) -> int:
    return min(100, 30 + features.velocity_x100 // 3)
