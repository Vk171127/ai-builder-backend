"""Convert raw client capture into normalized scam signals."""

from __future__ import annotations

import time

from app.models.signal import Behaviour, SignalBatch, SignalEvent, Source
from app.schemas.analyse import AnalyseRequest


class SignalProcessor:
    """Keyword/rule extraction from raw capture into normalized signal events."""


    AUTHORITY_WORDS = ("police", "cbi", "officer", "authority", "arrest", "trai")
    DRUG_WORDS = ("parcel", "drug", "courier", "narcotics")
    ISOLATION_WORDS = ("do not disconnect", "don\"t disconnect", "don't tell", "stay alone")

    @staticmethod
    def _contains_any(text: str, words: tuple[str, ...]) -> bool:
        lower = text.lower()
        return any(word in lower for word in words)

    async def to_signal_batch(self, request: AnalyseRequest) -> SignalBatch:
        if request.signals is not None and request.signals.events:
            return request.signals

        now_ms = int(time.time() * 1000)
        events: list[SignalEvent] = []

        voice_text = ""
        if request.raw_capture and request.raw_capture.voice and request.raw_capture.voice.transcript:
            voice_text = request.raw_capture.voice.transcript

        if voice_text:
            if self._contains_any(voice_text, self.AUTHORITY_WORDS):
                events.append(
                    SignalEvent(
                        event_id=f"raw-{len(events)+1}",
                        timestamp_ms=now_ms,
                        signal_type="voice_keyword",
                        source=Source.phone,
                        behaviour=Behaviour.authority_claim,
                        metadata={"remarks": voice_text[:240]},
                    )
                )
            if self._contains_any(voice_text, self.DRUG_WORDS):
                events.append(
                    SignalEvent(
                        event_id=f"raw-{len(events)+1}",
                        timestamp_ms=now_ms + 5,
                        signal_type="voice_keyword",
                        source=Source.phone,
                        behaviour=Behaviour.keyword_courier_drugs,
                        metadata={"detected_phrase": "courier_drugs_context"},
                    )
                )
            if self._contains_any(voice_text, self.ISOLATION_WORDS):
                events.append(
                    SignalEvent(
                        event_id=f"raw-{len(events)+1}",
                        timestamp_ms=now_ms + 10,
                        signal_type="voice_keyword",
                        source=Source.phone,
                        behaviour=Behaviour.isolation_demand,
                        metadata={"detected_phrase": "isolation_context"},
                    )
                )

        browser = request.raw_capture.browser if request.raw_capture else None
        if browser is not None:
            if browser.pasted_payee is True:
                events.append(
                    SignalEvent(
                        event_id=f"raw-{len(events)+1}",
                        timestamp_ms=now_ms + 20,
                        signal_type="browser_event",
                        source=Source.extension,
                        behaviour=Behaviour.paste_payee,
                        metadata={"payee_account": request.payment.payee_account or "unknown"},
                    )
                )
            if browser.pasted_amount is True:
                events.append(
                    SignalEvent(
                        event_id=f"raw-{len(events)+1}",
                        timestamp_ms=now_ms + 30,
                        signal_type="browser_event",
                        source=Source.extension,
                        behaviour=Behaviour.paste_amount,
                        metadata={},
                    )
                )
            if browser.pasted_otp is True:
                events.append(
                    SignalEvent(
                        event_id=f"raw-{len(events)+1}",
                        timestamp_ms=now_ms + 40,
                        signal_type="browser_event",
                        source=Source.extension,
                        behaviour=Behaviour.paste_otp,
                        metadata={},
                    )
                )
            if browser.url and any(x in browser.url.lower() for x in ("verify", "secure", "alert")):
                events.append(
                    SignalEvent(
                        event_id=f"raw-{len(events)+1}",
                        timestamp_ms=now_ms + 50,
                        signal_type="browser_event",
                        source=Source.extension,
                        behaviour=Behaviour.lookalike_domain,
                        metadata={"domain": request.payment.domain or browser.url},
                    )
                )

        if not events:
            events.append(
                SignalEvent(
                    event_id="raw-1",
                    timestamp_ms=now_ms,
                    signal_type="raw_capture_present",
                    source=Source.server,
                    behaviour=Behaviour.normal,
                    metadata={},
                )
            )

        return SignalBatch(session_id=request.session_id, events=events)


def get_signal_processor() -> SignalProcessor:
    return SignalProcessor()
