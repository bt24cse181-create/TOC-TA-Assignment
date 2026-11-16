"""Pydantic schemas for ProcessCase instances."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.case import CaseStatusEnum
from app.schemas.anomaly import AnomalyResultResponse
from app.schemas.event import EventLogResponse


class CaseCreateRequest(BaseModel):
    """Payload to instantiate a new workflow process instance."""

    workflow_code: str = Field(default="ONLINE_PAYMENT", min_length=1, max_length=50)
    case_id: Optional[str] = Field(default=None, max_length=64, description="Optional custom unique case ID; generated if omitted")
    total_amount: Optional[Decimal] = Field(default=None, ge=0, description="Transaction monetary amount")
    user_id: Optional[str] = Field(default=None, max_length=64, description="Initiator user identifier")
    metadata_json: Optional[Dict[str, Any]] = Field(default=None, description="Initial case metadata")


class CaseResponse(BaseModel):
    """Case details with current state, events, and anomalies."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: str
    workflow_id: int
    current_state_key: str
    status: CaseStatusEnum
    total_amount: Optional[Decimal] = None
    user_id: Optional[str] = None
    retry_count: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    metadata_json: Optional[Dict[str, Any]] = None
    events: List[EventLogResponse] = []
    anomalies: List[AnomalyResultResponse] = []


class CaseListItem(BaseModel):
    """Compact summary of a process case for table lists."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: str
    workflow_id: int
    current_state_key: str
    status: CaseStatusEnum
    total_amount: Optional[Decimal] = None
    retry_count: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    event_count: int = 0
    anomaly_count: int = 0
