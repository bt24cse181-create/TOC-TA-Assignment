"""Global anomaly analytics endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.anomaly import PaginatedAnomalyResponse
from app.services.case_service import CaseService

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


@router.get("", response_model=PaginatedAnomalyResponse)
def list_anomalies(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    case_id: Optional[str] = Query(default=None, description="Filter by case ID"),
    severity: Optional[str] = Query(default=None, description="Filter by severity: LOW, MEDIUM, HIGH, CRITICAL"),
    detector_type: Optional[str] = Query(default=None, description="Filter by detector: DFA, ISOLATION_FOREST, HYBRID"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated anomaly findings across all cases with optional filtering."""
    items, total = CaseService.get_anomalies(
        db,
        page=page,
        page_size=page_size,
        case_id=case_id,
        severity=severity,
        detector_type=detector_type,
    )
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedAnomalyResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
