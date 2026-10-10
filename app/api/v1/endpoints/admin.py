"""Admin-only operational endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/reset")
async def reset_runtime_state() -> dict[str, str]:
    """Reset in-memory runtime state (stub implementation)."""
    return {"status": "reset"}
