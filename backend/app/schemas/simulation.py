"""Pydantic schemas for batch trace simulation."""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SimulationEventInput(BaseModel):
    """Event representation within a simulation case."""

    event_name: str
    execution_duration_ms: Optional[int] = 0
    inter_event_delay_ms: Optional[int] = 0
    payload: Optional[Dict[str, Any]] = None


class SimulationCaseInput(BaseModel):
    """Case input for batch simulation."""

    case_id: str = Field(..., min_length=1, max_length=64)
    total_amount: Optional[Decimal] = Field(default=Decimal("100.00"), ge=0)
    user_id: Optional[str] = "sim_user"
    events: List[SimulationEventInput] = Field(default_factory=list)


class BatchSimulationRequest(BaseModel):
    """Batch simulation execution payload with request-size limits."""

    workflow_code: str = Field(default="ONLINE_PAYMENT", min_length=1, max_length=50)
    cases: List[SimulationCaseInput] = Field(..., min_length=1, max_length=100, description="List of traces (max 100 per batch)")
    persist_results: bool = Field(default=False, description="Whether to persist simulation cases into MySQL database")


class SimulationCaseResult(BaseModel):
    """Evaluation output for a single simulated trace."""

    case_id: str
    is_anomaly: bool
    classification: str
    severity: str
    final_state: str
    explanation: str
    evaluation: Dict[str, Any]
    error: Optional[str] = None


class BatchSimulationResponse(BaseModel):
    """Aggregated batch simulation response."""

    workflow_code: str
    total_cases: int
    processed_count: int
    anomalies_detected: int
    normal_count: int
    syntactic_anomalies: int
    behavioral_anomalies: int
    compound_anomalies: int
    results: List[SimulationCaseResult]
