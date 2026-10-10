"""API v1 router configuration."""

from fastapi import APIRouter
from app.api.v1.endpoints import admin, analyse, health, items, outcome, patterns

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router)
api_router.include_router(items.router)
api_router.include_router(analyse.router)
api_router.include_router(outcome.router)
api_router.include_router(patterns.router)
api_router.include_router(admin.router)
