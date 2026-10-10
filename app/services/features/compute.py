"""Feature computation from events and enrichment context."""

import statistics

from app.models.signal import SignalEvent
from app.schemas.feature import FeatureVector


def compute(
    events: list[SignalEvent],
    context: dict[str, int | str | bool | None],
    config: dict[str, int | str | bool | None],
) -> FeatureVector:
    _ = config
    behaviour_counts: dict[str, int] = {"normal": 0, "suspicious": 0, "malicious": 0}
    source_counts: dict[str, int] = {"phone": 0, "extension": 0, "server": 0}
    stage_counts: dict[str, int] = {
        "contact": 0,
        "trust_building": 0,
        "isolation": 0,
        "pressure": 0,
        "extraction": 0,
    }

    new_payee_count = 0
    amount_outlier_count = 0
    trust_values: list[int] = []
    contact_phone_count = 0
    trust_building_extension_count = 0
    isolation_extension_count = 0
    pressure_phone_count = 0
    extraction_server_count = 0

    for event in events:
        if event.behaviour is not None:
            key = str(event.behaviour.value)
            if key in behaviour_counts:
                behaviour_counts[key] += 1

        source = str(event.signal_type)
        if source in source_counts:
            source_counts[source] += 1

        stage = event.metadata.get("stage")
        if isinstance(stage, str) and stage in stage_counts:
            stage_counts[stage] += 1

            if stage == "contact" and source == "phone":
                contact_phone_count += 1
            elif stage == "trust_building" and source == "extension":
                trust_building_extension_count += 1
            elif stage == "isolation" and source == "extension":
                isolation_extension_count += 1
            elif stage == "pressure" and source == "phone":
                pressure_phone_count += 1
            elif stage == "extraction" and source == "server":
                extraction_server_count += 1

        if event.metadata.get("new_payee") is True:
            new_payee_count += 1
        if event.metadata.get("amount_outlier") is True:
            amount_outlier_count += 1

        if event.value_x100 is not None:
            trust_values.append(event.value_x100)

    avg_trust = int(sum(trust_values) / len(trust_values)) if trust_values else 0
    baseline_trust = context.get("baseline_trust_x100")
    if isinstance(baseline_trust, int):
        profile_trust_x100 = max(0, min(100, (avg_trust + baseline_trust) // 2))
    else:
        profile_trust_x100 = max(0, min(100, avg_trust))

    trust_std = int(statistics.pstdev(trust_values)) if len(trust_values) > 1 else 0
    event_count = len(events)
    suspicious_ratio = (
        int((behaviour_counts["suspicious"] * 100) / event_count) if event_count > 0 else 0
    )
    malicious_ratio = (
        int((behaviour_counts["malicious"] * 100) / event_count) if event_count > 0 else 0
    )

    return FeatureVector(
        event_count=len(events),
        high_risk_event_count=sum(1 for event in events if (event.value_x100 or 0) > 80),
        velocity_x100=min(100, len(events) * 5),
        profile_trust_x100=profile_trust_x100,
        normal_count=behaviour_counts["normal"],
        suspicious_count=behaviour_counts["suspicious"],
        malicious_count=behaviour_counts["malicious"],
        phone_count=source_counts["phone"],
        extension_count=source_counts["extension"],
        server_count=source_counts["server"],
        new_payee_count=new_payee_count,
        amount_outlier_count=amount_outlier_count,
        contact_count=stage_counts["contact"],
        trust_building_count=stage_counts["trust_building"],
        isolation_count=stage_counts["isolation"],
        pressure_count=stage_counts["pressure"],
        extraction_count=stage_counts["extraction"],
        avg_trust_x100=max(0, min(100, avg_trust)),
        std_trust_x100=max(0, min(100, trust_std)),
        suspicious_ratio_x100=max(0, min(100, suspicious_ratio)),
        malicious_ratio_x100=max(0, min(100, malicious_ratio)),
        contact_phone_count=contact_phone_count,
        trust_building_extension_count=trust_building_extension_count,
        isolation_extension_count=isolation_extension_count,
        pressure_phone_count=pressure_phone_count,
        extraction_server_count=extraction_server_count,
    )
