"""SQLAlchemy ORM models for workflows, states, and transition rules."""

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StateTypeEnum(str, enum.Enum):
    """Classification of automaton state types."""

    START = "START"
    INTERMEDIATE = "INTERMEDIATE"
    TERMINAL_SUCCESS = "TERMINAL_SUCCESS"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    ERROR = "ERROR"


class Workflow(Base):
    """Registered business process workflow definition."""

    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    # Relationships
    states: Mapped[List["WorkflowState"]] = relationship(
        "WorkflowState",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowState.id",
    )
    transitions: Mapped[List["WorkflowTransition"]] = relationship(
        "WorkflowTransition",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
    cases: Mapped[List["ProcessCase"]] = relationship(  # type: ignore # noqa: F821
        "ProcessCase",
        back_populates="workflow",
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, code='{self.code}', version={self.version})>"


class WorkflowState(Base):
    """A formal state q in DFA Q for a given workflow."""

    __tablename__ = "workflow_states"
    __table_args__ = (
        UniqueConstraint("workflow_id", "state_key", name="uq_workflow_state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    state_key: Mapped[str] = mapped_column(String(50), nullable=False)
    state_name: Mapped[str] = mapped_column(String(100), nullable=False)
    state_type: Mapped[StateTypeEnum] = mapped_column(
        Enum(StateTypeEnum, name="state_type_enum"), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_initial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="states")
    outgoing_transitions: Mapped[List["WorkflowTransition"]] = relationship(
        "WorkflowTransition",
        foreign_keys="[WorkflowTransition.from_state_id]",
        back_populates="from_state",
        cascade="all, delete-orphan",
    )
    incoming_transitions: Mapped[List["WorkflowTransition"]] = relationship(
        "WorkflowTransition",
        foreign_keys="[WorkflowTransition.to_state_id]",
        back_populates="to_state",
        cascade="all, delete-orphan",
    )
    cases: Mapped[List["ProcessCase"]] = relationship(  # type: ignore # noqa: F821
        "ProcessCase",
        foreign_keys="[ProcessCase.current_state_id]",
        back_populates="current_state",
    )

    def __repr__(self) -> str:
        return f"<WorkflowState(id={self.id}, key='{self.state_key}', type='{self.state_type}')>"


class WorkflowTransition(Base):
    """Permitted transition function delta(from_state, event_name) = to_state."""

    __tablename__ = "workflow_transitions"
    __table_args__ = (
        UniqueConstraint("workflow_id", "from_state_id", "event_name", name="uq_state_event"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    from_state_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=False
    )
    to_state_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=False
    )
    event_name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    condition_meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="transitions")
    from_state: Mapped["WorkflowState"] = relationship(
        "WorkflowState", foreign_keys=[from_state_id], back_populates="outgoing_transitions"
    )
    to_state: Mapped["WorkflowState"] = relationship(
        "WorkflowState", foreign_keys=[to_state_id], back_populates="incoming_transitions"
    )

    def __repr__(self) -> str:
        return f"<WorkflowTransition(from={self.from_state_id}, event='{self.event_name}', to={self.to_state_id})>"
