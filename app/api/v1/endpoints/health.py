"""Health check endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the health status and version of the API.
    """
    from app import __version__

    return HealthResponse(status="healthy", version=__version__)


@router.get("/ready", response_model=HealthResponse, tags=["Health"])
async def readiness_check() -> HealthResponse:
    """
    Readiness check endpoint.

    Returns whether the service is ready to accept requests.
    """
    from app import __version__

    return HealthResponse(status="ready", version=__version__)
