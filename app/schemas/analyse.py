"""Request/response schemas for analyse API."""

from pydantic import BaseModel, model_validator

from app.models.decision import Decision
from app.models.signal import SignalBatch, SignalEvent


class PaymentContext(BaseModel):
    amount_minor: int | None = None
    currency: str | None = None
    payee_account: str | None = None
    referrer_url: str | None = None
    domain: str | None = None
    customer_id: str | None = None


class VoiceCapture(BaseModel):
    transcript: str | None = None
    audio_gcs_uri: str | None = None
    language: str | None = None


class BrowserCapture(BaseModel):
    url: str | None = None
    page_title: str | None = None
    dom_text: str | None = None
    pasted_payee: bool | None = None
    pasted_amount: bool | None = None
    pasted_otp: bool | None = None


class RawCapture(BaseModel):
    captured_at_ms: int | None = None
    voice: VoiceCapture | None = None
    browser: BrowserCapture | None = None
    notes: str | None = None


class AnalyseRequest(BaseModel):
    session_id: str
    signals: SignalBatch | None = None
    raw_capture: RawCapture | None = None
    payment: PaymentContext
    session_locale: str = "en"

    @model_validator(mode="before")
    @classmethod
    def _normalize_payload(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        if "signals" not in value:
            events = value.get("events", [])
            value["signals"] = {"session_id": value.get("session_id", ""), "events": events}
        if "payment" not in value:
            value["payment"] = {}
        return value

    @model_validator(mode="after")
    def _require_input_source(self) -> "AnalyseRequest":
        has_signals = self.signals is not None
        has_raw = self.raw_capture is not None
        if not has_signals and not has_raw:
            raise ValueError("Provide either signals.events or raw_capture")
        return self

    @property
    def events(self) -> list[SignalEvent]:
        return self.signals.events if self.signals is not None else []


class AnalyseResponse(BaseModel):
    decision: Decision
