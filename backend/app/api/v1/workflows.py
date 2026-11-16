"""Workflow query endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.workflow import WorkflowListItem, WorkflowResponse
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.get("", response_model=List[WorkflowListItem])
def list_workflows(db: Session = Depends(get_db)):
    """Retrieve all configured workflow definitions."""
    workflows = WorkflowService.get_all_workflows(db)
    items = []
    for w in workflows:
        items.append(
            WorkflowListItem(
                id=w.id,
                code=w.code,
                name=w.name,
                description=w.description,
                version=w.version,
                is_active=w.is_active,
                created_at=w.created_at,
                state_count=len(w.states),
                transition_count=len(w.transitions),
            )
        )
    return items


@router.get("/{identifier}", response_model=WorkflowResponse)
def get_workflow(identifier: str, db: Session = Depends(get_db)):
    """Retrieve complete workflow definition including state space Q and transition matrix delta."""
    wf = WorkflowService.get_workflow_by_id_or_code(db, identifier)
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{identifier}' not found.",
        )
    return wf
