"""Risk fusion layer based on policy weights."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.models.signal import SignalEvent, Stage


def _load_policy(path: Path = Path("policy.yaml")) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def fuse_risk(
    *,
    rule_floor: float,
    classifier_max_prob: float,
    novelty: float,
    reasoner_likelihood: float,
    graph_boost: float,
    top_stage: Stage,
    events: list[SignalEvent],
    policy_path: Path = Path("policy.yaml"),
) -> float:
    policy = _load_policy(policy_path)
    w1 = float(policy.get("w1", 0.45))
    w2 = float(policy.get("w2", 0.25))
    w3 = float(policy.get("w3", 0.20))
    w4 = float(policy.get("w4", 0.10))

    risk = max(
        rule_floor,
        (w1 * classifier_max_prob) + (w2 * novelty) + (w3 * reasoner_likelihood) + (w4 * graph_boost),
    )

    multipliers = policy.get("stage_multipliers", {})
    stage_multiplier = float(multipliers.get(top_stage.value, 1.0)) if isinstance(multipliers, dict) else 1.0
    risk *= stage_multiplier

    if events and all(float(event.trust or 0.0) < 0.7 for event in events):
        ceiling = float(policy.get("source_trust_ceiling", 0.75))
        risk = min(risk, ceiling)

    return max(0.0, min(1.0, risk))
