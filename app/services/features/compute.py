"""Feature computation for Gatekeeper hot-path."""

from __future__ import annotations

import math
from collections import defaultdict

from app.models.signal import Behaviour, SignalEvent
from app.schemas.feature import FeatureVector


COERCION_BEHAVIOURS = {
    Behaviour.authority_claim,
    Behaviour.keyword_authority,
    Behaviour.keyword_courier_drugs,
    Behaviour.isolation_demand,
}
PAYMENT_BEHAVIOURS = {Behaviour.new_payee, Behaviour.paste_payee}


def _safe_nan(values: dict[str, float], missing: dict[str, bool], key: str) -> None:
    values[key] = float("nan")
    missing[f"{key}_missing"] = True


def compute(
    events: list[SignalEvent],
    context: dict[str, object],
    config: dict[str, object],
) -> FeatureVector:
    if not events:
        values = {name: float("nan") for name in FeatureVector.FEATURE_ORDER}
        missing = {f"{name}_missing": True for name in FeatureVector.FEATURE_ORDER}
        return FeatureVector(values=values, missing_flags=missing)

    ordered = sorted(events, key=lambda event: event.timestamp_ms)
    values: dict[str, float] = {}
    missing: dict[str, bool] = {}

    # Group A: Presence
    for key in ["normal", "suspicious", "malicious"]:
        bucket = [event for event in ordered if event.behaviour is not None and event.behaviour.value == key]
        values[f"presence_{key}"] = 1.0 if bucket else 0.0
        weighted = sum(float(event.trust or 0.0) for event in bucket)
        values[f"trust_weighted_{key}"] = weighted / len(bucket) if bucket else 0.0
        missing[f"presence_{key}_missing"] = False
        missing[f"trust_weighted_{key}_missing"] = False

    timestamps = [event.timestamp_ms for event in ordered]
    duration_s = max(1.0, float(timestamps[-1] - timestamps[0]) / 1000.0)

    # Group B: Temporal
    values["session_duration_s"] = duration_s
    values["burst_density"] = float(len(ordered)) / duration_s
    missing["session_duration_s_missing"] = False
    missing["burst_density_missing"] = False

    # authority_before_payment
    authority_times = [event.timestamp_ms for event in ordered if event.behaviour in COERCION_BEHAVIOURS]
    payment_times = [event.timestamp_ms for event in ordered if event.behaviour in PAYMENT_BEHAVIOURS]
    if authority_times and payment_times:
        values["authority_before_payment"] = 1.0 if min(authority_times) <= min(payment_times) else 0.0
        missing["authority_before_payment_missing"] = False
    else:
        _safe_nan(values, missing, "authority_before_payment")

    gaps = [
        float(ordered[index].timestamp_ms - ordered[index - 1].timestamp_ms) / 1000.0
        for index in range(1, len(ordered))
    ]
    values["max_inter_event_gap_s"] = max(gaps) if gaps else 0.0
    missing["max_inter_event_gap_s_missing"] = False

    # Group C: Cross-device
    cross_window_s = float(config.get("cross_device_window_s", 300))
    coercion_events = [event for event in ordered if event.source.value == "phone" and event.behaviour in COERCION_BEHAVIOURS]
    payment_events = [event for event in ordered if event.source.value == "extension" and event.behaviour in PAYMENT_BEHAVIOURS]

    pair_gaps: list[float] = []
    for coercion in coercion_events:
        for payment in payment_events:
            gap_s = abs(float(payment.timestamp_ms - coercion.timestamp_ms) / 1000.0)
            if gap_s <= cross_window_s:
                pair_gaps.append(gap_s)

    values["has_cross_device_coercion"] = 1.0 if pair_gaps else 0.0
    missing["has_cross_device_coercion_missing"] = False

    if pair_gaps:
        values["cross_device_gap_s"] = min(pair_gaps)
        missing["cross_device_gap_s_missing"] = False
    else:
        _safe_nan(values, missing, "cross_device_gap_s")

    # Group D: Context
    amounts = [
        int(event.metadata["amount_minor"])
        for event in ordered
        if isinstance(event.metadata.get("amount_minor"), int)
    ]
    profile_avg = context.get("avg_payment_minor")
    if amounts and isinstance(profile_avg, (int, float)) and float(profile_avg) > 0:
        values["amount_ratio"] = float(max(amounts)) / float(profile_avg)
        missing["amount_ratio_missing"] = False
    else:
        _safe_nan(values, missing, "amount_ratio")

    if any(event.metadata.get("new_payee") is True for event in ordered):
        values["payee_is_new"] = 1.0
    elif any(event.metadata.get("new_payee") is False for event in ordered):
        values["payee_is_new"] = 0.0
    else:
        _safe_nan(values, missing, "payee_is_new")
    if "payee_is_new" in values:
        missing["payee_is_new_missing"] = False

    if timestamps:
        event_hour = ((timestamps[0] // 1000) // 3600) % 24
        usual_hour = context.get("usual_hour")
        if isinstance(usual_hour, (int, float)):
            values["hour_deviation"] = float(abs(int(event_hour) - int(usual_hour)))
            missing["hour_deviation_missing"] = False
        else:
            _safe_nan(values, missing, "hour_deviation")

    # Group E: Reputation
    mule_score = context.get("payee_mule_score")
    if isinstance(mule_score, (int, float)):
        values["payee_mule_score"] = float(mule_score)
        missing["payee_mule_score_missing"] = False
    else:
        _safe_nan(values, missing, "payee_mule_score")

    web_risk_flagged = context.get("web_risk_flagged")
    values["web_risk_flagged"] = 1.0 if web_risk_flagged is True else 0.0
    missing["web_risk_flagged_missing"] = False

    in_graph = context.get("payee_in_graph")
    values["payee_in_graph"] = 1.0 if in_graph is True else 0.0
    missing["payee_in_graph_missing"] = False

    # Ensure all features exist with explicit missing semantics
    for name in FeatureVector.FEATURE_ORDER:
        if name not in values:
            _safe_nan(values, missing, name)

    return FeatureVector(values=values, missing_flags=missing)
