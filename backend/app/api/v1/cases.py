"""Process case and event management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.anomaly import AnomalyResultResponse
from app.schemas.case import CaseCreateRequest, CaseResponse
from app.schemas.event import EventSubmissionResponse, EventSubmitRequest
from app.services.case_service import CaseService

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(request: CaseCreateRequest, db: Session = Depends(get_db)):
    """Create and initialize a new business process execution case."""
    case = CaseService.create_case(db, request)
    # Reload with relationships
    return CaseService.get_case(db, case.case_id)


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db)):
    """Get full state, event logs, and anomaly verdicts for a specific case."""
    return CaseService.get_case(db, case_id)


@router.post("/{case_id}/events", response_model=EventSubmissionResponse)
def submit_event(
    case_id: str,
    request: EventSubmitRequest,
    db: Session = Depends(get_db),
):
    """Trigger a workflow transition event and re-analyze case through Hybrid Engine."""
    return CaseService.submit_event(db, case_id, request)


@router.get("/{case_id}/anomalies", response_model=List[AnomalyResultResponse])
def get_case_anomalies(case_id: str, db: Session = Depends(get_db)):
    """Get all anomaly detections associated with a specific case."""
    items, _ = CaseService.get_anomalies(db, case_id=case_id, page=1, page_size=100)
    return items
