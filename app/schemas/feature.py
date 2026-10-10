"""Feature vector schema."""

from dataclasses import dataclass

FEATURE_ORDER: tuple[str, ...] = (
    "event_count",
    "high_risk_event_count",
    "velocity_x100",
    "profile_trust_x100",
    "normal_count",
    "suspicious_count",
    "malicious_count",
    "phone_count",
    "extension_count",
    "server_count",
    "new_payee_count",
    "amount_outlier_count",
    "contact_count",
    "trust_building_count",
    "isolation_count",
    "pressure_count",
    "extraction_count",
    "avg_trust_x100",
    "std_trust_x100",
    "suspicious_ratio_x100",
    "malicious_ratio_x100",
    "contact_phone_count",
    "trust_building_extension_count",
    "isolation_extension_count",
    "pressure_phone_count",
    "extraction_server_count",
)


@dataclass(slots=True)
class FeatureVector:
    event_count: int
    high_risk_event_count: int
    velocity_x100: int
    profile_trust_x100: int
    normal_count: int
    suspicious_count: int
    malicious_count: int
    phone_count: int
    extension_count: int
    server_count: int
    new_payee_count: int
    amount_outlier_count: int
    contact_count: int
    trust_building_count: int
    isolation_count: int
    pressure_count: int
    extraction_count: int
    avg_trust_x100: int
    std_trust_x100: int
    suspicious_ratio_x100: int
    malicious_ratio_x100: int
    contact_phone_count: int
    trust_building_extension_count: int
    isolation_extension_count: int
    pressure_phone_count: int
    extraction_server_count: int

    def to_ordered_list(self) -> list[int]:
        return [
            self.event_count,
            self.high_risk_event_count,
            self.velocity_x100,
            self.profile_trust_x100,
            self.normal_count,
            self.suspicious_count,
            self.malicious_count,
            self.phone_count,
            self.extension_count,
            self.server_count,
            self.new_payee_count,
            self.amount_outlier_count,
            self.contact_count,
            self.trust_building_count,
            self.isolation_count,
            self.pressure_count,
            self.extraction_count,
            self.avg_trust_x100,
            self.std_trust_x100,
            self.suspicious_ratio_x100,
            self.malicious_ratio_x100,
            self.contact_phone_count,
            self.trust_building_extension_count,
            self.isolation_extension_count,
            self.pressure_phone_count,
            self.extraction_server_count,
        ]
