"""API v1 router registry."""

from fastapi import APIRouter

from app.api.v1.anomalies import router as anomalies_router
from app.api.v1.cases import router as cases_router
from app.api.v1.health import router as health_router
from app.api.v1.simulation import router as simulation_router
from app.api.v1.workflows import router as workflows_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(workflows_router)
api_v1_router.include_router(cases_router)
api_v1_router.include_router(anomalies_router)
api_v1_router.include_router(simulation_router)

__all__ = ["api_v1_router"]
