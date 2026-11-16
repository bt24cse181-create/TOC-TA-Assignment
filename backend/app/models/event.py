"""SQLAlchemy ORM model for process event logs (execution traces)."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EventLog(Base):
    """Immutable log entry recording an event execution within a case trace."""

    __tablename__ = "event_logs"
    __table_args__ = (
        Index("idx_event_case_time", "case_id", "timestamp"),
        Index("idx_event_name", "event_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("process_cases.case_id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_name: Mapped[str] = mapped_column(String(50), nullable=False)
    from_state_key: Mapped[str] = mapped_column(String(50), nullable=False)
    to_state_key: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    execution_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    case: Mapped["ProcessCase"] = relationship("ProcessCase", back_populates="events")  # type: ignore # noqa: F821
    anomalies: Mapped[List["AnomalyResult"]] = relationship(  # type: ignore # noqa: F821
        "AnomalyResult",
        back_populates="event_log",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<EventLog(id={self.id}, case='{self.case_id}', event='{self.event_name}', "
            f"transition='{self.from_state_key}->{self.to_state_key}')>"
        )
