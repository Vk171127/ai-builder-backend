"""Rule detector stub (YAML-driven)."""

from app.schemas.feature import FeatureVector


def score_rules(features: FeatureVector) -> int:
    return min(100, features.high_risk_event_count * 20)
