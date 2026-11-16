"""SQLAlchemy ORM model for process cases (workflow execution instances)."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DECIMAL,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CaseStatusEnum(str, enum.Enum):
    """Runtime execution status of a process case."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ANOMALOUS = "ANOMALOUS"


class ProcessCase(Base):
    """An instance or trace of a business workflow execution."""

    __tablename__ = "process_cases"
    __table_args__ = (
        Index("idx_cases_status", "status"),
        Index("idx_cases_started_at", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    workflow_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflows.id", ondelete="RESTRICT"), nullable=False
    )
    current_state_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflow_states.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[CaseStatusEnum] = mapped_column(
        Enum(CaseStatusEnum, name="case_status_enum"),
        nullable=False,
        default=CaseStatusEnum.RUNNING,
    )
    total_amount: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(12, 2), nullable=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="cases")  # type: ignore # noqa: F821
    current_state: Mapped["WorkflowState"] = relationship(  # type: ignore # noqa: F821
        "WorkflowState",
        foreign_keys=[current_state_id],
        back_populates="cases",
    )
    events: Mapped[List["EventLog"]] = relationship(  # type: ignore # noqa: F821
        "EventLog",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="EventLog.timestamp",
    )
    anomalies: Mapped[List["AnomalyResult"]] = relationship(  # type: ignore # noqa: F821
        "AnomalyResult",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="AnomalyResult.detected_at",
    )

    def __repr__(self) -> str:
        return f"<ProcessCase(case_id='{self.case_id}', status='{self.status}', retries={self.retry_count})>"

    @property
    def current_state_key(self) -> str:
        """Helper property exposing the string key of the current state."""
        return self.current_state.state_key if self.current_state else ""
