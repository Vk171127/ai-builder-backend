"""Decision model outputs."""

from pydantic import BaseModel

from app.models.signal import Stage


class Intervention(BaseModel):
    code: str
    message: str


class ReasonerResult(BaseModel):
    explanation: str
    confidence_x100: int


class Decision(BaseModel):
    id: str
    session_id: str
    risk_x100: int
    stage: Stage
    intervention: Intervention | None = None
    reasoner: ReasonerResult | None = None
