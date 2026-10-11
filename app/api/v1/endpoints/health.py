"""Health check endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.pipeline_service import get_pipeline_service

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str


@router.get("/healthz", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the health status and version of the API.
    """
    from app import __version__
    return HealthResponse(status="healthy", version=__version__)


@router.get("/readyz", response_model=HealthResponse, tags=["Health"])
async def readiness_check() -> HealthResponse:
    """
    Readiness check endpoint.

    Returns whether the service is ready to accept requests.
    """
    from app import __version__
    try:
        state_ok = bool(get_pipeline_service().state.ping())
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"state store unavailable: {exc}") from exc

    model_ok = get_pipeline_service().models_loaded()
    if not state_ok or not model_ok:
        raise HTTPException(status_code=503, detail="service not ready")
    return HealthResponse(status="ready", version=__version__)
