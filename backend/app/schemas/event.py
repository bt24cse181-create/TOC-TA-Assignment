"""Pydantic schemas for process event logging and submission."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class EventSubmitRequest(BaseModel):
    """Payload to trigger a process step transition."""

    event_name: str = Field(..., min_length=1, max_length=50, description="Alphabet symbol to execute")
    execution_duration_ms: Optional[int] = Field(default=0, ge=0, description="Step execution time in ms")
    payload_json: Optional[Dict[str, Any]] = Field(default=None, description="Contextual payload metadata")
    idempotency_key: Optional[str] = Field(default=None, max_length=64, description="Optional key to prevent duplicate step submissions")


class EventLogResponse(BaseModel):
    """Immutable execution event record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: str
    workflow_id: int
    event_name: str
    from_state_key: str
    to_state_key: str
    timestamp: datetime
    execution_duration_ms: int
    retry_count: int
    payload_json: Optional[Dict[str, Any]] = None


class EventSubmissionResponse(BaseModel):
    """Response returned after submitting an event to a case."""

    case_id: str
    current_state: str
    status: str
    event: EventLogResponse
    evaluation: Dict[str, Any]
