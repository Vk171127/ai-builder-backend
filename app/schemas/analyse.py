"""Request/response schemas for analyse API."""

from pydantic import BaseModel

from app.models.decision import Decision
from app.models.signal import SignalEvent


class AnalyseRequest(BaseModel):
    session_id: str
    events: list[SignalEvent]


class AnalyseResponse(BaseModel):
    decision: Decision
