"""Analyse endpoints."""

from uuid import uuid4

from fastapi import APIRouter

from app.schemas.analyse import AnalyseRequest, AnalyseResponse
from app.services.pipeline_service import PipelineService

router = APIRouter(tags=["Analyse"])
_service = PipelineService()


@router.post("/analyse", response_model=AnalyseResponse)
async def analyse(request: AnalyseRequest) -> AnalyseResponse:
    """Run the Gatekeeper decision pipeline."""
    decision = await _service.run(request)
    return AnalyseResponse(decision=decision)


@router.get("/decisions/{decision_id}", response_model=AnalyseResponse)
async def get_decision(decision_id: str) -> AnalyseResponse:
    """Return a decision by id.

    Stubbed for initial scaffolding.
    """
    request = AnalyseRequest(session_id=f"lookup-{decision_id}", events=[])
    decision = await _service.run(request)
    decision.id = decision_id or str(uuid4())
    return AnalyseResponse(decision=decision)
