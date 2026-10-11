"""Signal models for transactional behaviour streams."""

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel


class Behaviour(str, Enum):
    normal = "normal"
    suspicious = "suspicious"
    malicious = "malicious"
    authority_claim = "AUTHORITY_CLAIM"
    keyword_authority = "KEYWORD_AUTHORITY"
    keyword_courier_drugs = "KEYWORD_COURIER_DRUGS"
    keyword_investment_returns = "KEYWORD_INVESTMENT_RETURNS"
    isolation_demand = "ISOLATION_DEMAND"
    screen_share_likely = "SCREEN_SHARE_LIKELY"
    second_voice = "SECOND_VOICE"
    new_payee = "NEW_PAYEE"
    paste_payee = "PASTE_PAYEE"
    paste_amount = "PASTE_AMOUNT"
    paste_otp = "PASTE_OTP"
    otp_too_fast = "OTP_TOO_FAST"
    card_otp_form = "CARD_OTP_FORM"
    lookalike_domain = "LOOKALIKE_DOMAIN"
    homoglyph_domain = "HOMOGLYPH_DOMAIN"
    unknown_device = "UNKNOWN_DEVICE"
    remote_access_tool_open = "REMOTE_ACCESS_TOOL_OPEN"
    amount_outlier = "AMOUNT_OUTLIER"

    @property
    def human_description(self) -> str:
        mapping = {
            Behaviour.normal: "Normal behavior observed",
            Behaviour.suspicious: "Suspicious behavior observed",
            Behaviour.malicious: "Malicious behavior observed",
            Behaviour.authority_claim: "Authority claim detected",
            Behaviour.keyword_authority: "Authority keyword detected",
            Behaviour.keyword_courier_drugs: "Courier-drugs threat keyword detected",
            Behaviour.keyword_investment_returns: "High-return investment keyword detected",
            Behaviour.isolation_demand: "Isolation demand detected",
            Behaviour.screen_share_likely: "Screen share coercion signal detected",
            Behaviour.second_voice: "Second voice influence detected",
            Behaviour.new_payee: "New payee action detected",
            Behaviour.paste_payee: "Pasted payee details detected",
            Behaviour.paste_amount: "Pasted amount detected",
            Behaviour.paste_otp: "Pasted OTP detected",
            Behaviour.otp_too_fast: "Unusually fast OTP entry detected",
            Behaviour.card_otp_form: "Card OTP form detected",
            Behaviour.lookalike_domain: "Lookalike domain detected",
            Behaviour.homoglyph_domain: "Homoglyph domain detected",
            Behaviour.unknown_device: "Unknown device detected",
            Behaviour.remote_access_tool_open: "Remote access tool activity detected",
            Behaviour.amount_outlier: "Amount outlier detected",
        }
        return mapping.get(self, self.value)

    @property
    def default_trust(self) -> float:
        if self in {Behaviour.normal}:
            return 0.6
        if self in {Behaviour.suspicious}:
            return 0.4
        if self in {Behaviour.malicious}:
            return 0.2
        suspicious_like = {
            Behaviour.new_payee,
            Behaviour.paste_payee,
            Behaviour.paste_amount,
            Behaviour.lookalike_domain,
            Behaviour.homoglyph_domain,
            Behaviour.amount_outlier,
            Behaviour.keyword_investment_returns,
        }
        return 0.45 if self in suspicious_like else 0.25


class Source(str, Enum):
    phone = "phone"
    extension = "extension"
    server = "server"


class Stage(str, Enum):
    contact = "contact"
    trust_building = "trust_building"
    isolation = "isolation"
    pressure = "pressure"
    extraction = "extraction"


class ScamType(str, Enum):
    benign = "benign"
    digital_arrest = "digital_arrest"
    phishing_credential = "phishing_credential"
    bank_official_vishing = "bank_official_vishing"
    investment = "investment"
    remote_access_support = "remote_access_support"
    unknown = "unknown"


class SignalEvent(BaseModel):
    event_id: str
    timestamp_ms: int
    signal_type: str
    source: Source
    value_x100: int | None = None
    trust: float | None = None
    behaviour: Behaviour | None = None
    metadata: dict[str, str | int | bool | None] = {}


class SignalBatch(BaseModel):
    session_id: str
    events: list[SignalEvent]


@dataclass(slots=True)
class RejectedEvent:
    event_id: str
    reason: str


@dataclass(slots=True)
class ValidatedBatch:
    accepted: list[SignalEvent]
    rejected_with_reasons: list[RejectedEvent]
