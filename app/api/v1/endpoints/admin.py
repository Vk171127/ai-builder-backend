"""Admin-only operational endpoints."""

from fastapi import APIRouter
from app.services.pipeline_service import get_pipeline_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/reset")
async def reset_runtime_state() -> dict[str, bool]:
    """Reset runtime keys for sessions and warning cache."""
    keys = get_pipeline_service().state.keys("session:*") + get_pipeline_service().state.keys("warn_cache:*")
    if keys:
        get_pipeline_service().state.delete(*keys)
    return {"ok": True}
