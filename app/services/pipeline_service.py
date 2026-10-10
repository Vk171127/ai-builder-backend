"""Main orchestration service for analyse requests."""

from uuid import uuid4

from app.models.decision import Decision, Intervention
from app.models.signal import Stage
from app.schemas.analyse import AnalyseRequest


class PipelineService:
    """Coordinates all Gatekeeper stages and returns a final decision."""

    async def run(self, request: AnalyseRequest) -> Decision:
        risk_x100 = min(100, len(request.events) * 10)
        stage = Stage.observe if risk_x100 < 40 else Stage.warn
        intervention = (
            None
            if stage == Stage.observe
            else Intervention(code="warn_generic", message="Potential scam indicators detected")
        )
        return Decision(
            id=str(uuid4()),
            session_id=request.session_id,
            risk_x100=risk_x100,
            stage=stage,
            intervention=intervention,
        )
