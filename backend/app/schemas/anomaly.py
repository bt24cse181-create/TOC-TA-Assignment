"""Pydantic schemas for AnomalyResult entities."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

from app.models.anomaly import AnomalySeverityEnum, DetectorTypeEnum


class AnomalyResultResponse(BaseModel):
    """Detection verdict record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: str
    event_log_id: Optional[int] = None
    detector_type: DetectorTypeEnum
    is_anomaly: bool
    anomaly_score: Optional[float] = None
    anomaly_reason: str
    severity: AnomalySeverityEnum
    rule_violation: Optional[str] = None
    detected_at: datetime
    details_json: Optional[Dict[str, Any]] = None


class PaginatedAnomalyResponse(BaseModel):
    """Paginated collection of anomaly records."""

    items: List[AnomalyResultResponse]
    total: int
    page: int
    page_size: int
    pages: int
