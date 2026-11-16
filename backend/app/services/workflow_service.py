"""Workflow service handling workflow queries and DFA engine caching."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.engine.dfa_engine import DFAEngine, get_online_payment_dfa
from app.models.workflow import Workflow


class WorkflowService:
    """Service layer for workflow definitions."""

    @staticmethod
    def get_all_workflows(session: Session) -> List[Workflow]:
        """Fetch all registered workflows with their states and transitions."""
        stmt = (
            select(Workflow)
            .options(
                selectinload(Workflow.states),
                selectinload(Workflow.transitions),
            )
            .order_by(Workflow.id)
        )
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_workflow_by_id_or_code(session: Session, identifier: str) -> Optional[Workflow]:
        """Fetch a specific workflow by primary key ID or unique code."""
        stmt = select(Workflow).options(
            selectinload(Workflow.states),
            selectinload(Workflow.transitions),
        )
        if identifier.isdigit():
            stmt = stmt.where(Workflow.id == int(identifier))
        else:
            stmt = stmt.where(Workflow.code == identifier)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_dfa_for_workflow(workflow: Optional[Workflow]) -> DFAEngine:
        """Construct or retrieve a DFAEngine for the given workflow."""
        if workflow and workflow.code == "ONLINE_PAYMENT":
            # Can use in-memory fast representation or DB representation
            try:
                return DFAEngine.from_db_workflow(workflow)
            except Exception:
                return get_online_payment_dfa()
        elif workflow:
            return DFAEngine.from_db_workflow(workflow)
        return get_online_payment_dfa()
