"""Pydantic schemas for Workflow entities."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

from app.models.workflow import StateTypeEnum


class WorkflowStateResponse(BaseModel):
    """Workflow state information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    state_key: str
    state_name: str
    state_type: StateTypeEnum
    is_initial: bool
    is_terminal: bool
    description: Optional[str] = None


class WorkflowTransitionResponse(BaseModel):
    """Workflow transition rule."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    from_state_id: int
    to_state_id: int
    event_name: str
    is_allowed: bool
    max_retries: int
    condition_meta: Optional[Dict[str, Any]] = None


class WorkflowResponse(BaseModel):
    """Full workflow definition including states and transitions."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: Optional[str] = None
    version: int
    is_active: bool
    created_at: datetime
    states: List[WorkflowStateResponse] = []
    transitions: List[WorkflowTransitionResponse] = []


class WorkflowListItem(BaseModel):
    """Lightweight workflow summary for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: Optional[str] = None
    version: int
    is_active: bool
    created_at: datetime
    state_count: int = 0
    transition_count: int = 0
