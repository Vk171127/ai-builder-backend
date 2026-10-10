"""Anomaly detector stub (IsolationForest + z-scores)."""

from app.schemas.feature import FeatureVector


def score_anomaly(features: FeatureVector) -> int:
    return min(100, features.event_count * 8)
