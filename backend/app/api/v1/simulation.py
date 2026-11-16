"""Batch trace simulation endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.simulation import (
    BatchSimulationRequest,
    BatchSimulationResponse,
)
from app.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulation", tags=["Simulation"])


@router.post("/run-batch", response_model=BatchSimulationResponse)
def run_batch_simulation(
    request: BatchSimulationRequest,
    db: Session = Depends(get_db),
):
    """Evaluate a batch of synthetic or supplied execution traces against the Hybrid Engine."""
    return SimulationService.run_batch_simulation(db, request)
