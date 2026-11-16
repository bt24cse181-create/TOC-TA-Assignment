"""Integration tests validating DFAEngine loaded directly from MySQL ORM models."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.engine.dfa_engine import DFAEngine, get_online_payment_dfa
from app.models.workflow import Workflow


def test_dfa_from_database_models():
    """Verify that DFAEngine loaded from MySQL matches expected behavior."""
    try:
        with SessionLocal() as session:
            stmt = (
                select(Workflow)
                .where(Workflow.code == "ONLINE_PAYMENT")
                .options(
                    selectinload(Workflow.states),
                    selectinload(Workflow.transitions),
                )
            )
            workflow = session.execute(stmt).scalar_one_or_none()
    except Exception as exc:
        pytest.skip(f"Live database not accessible: {exc}")

    if not workflow:
        pytest.skip("ONLINE_PAYMENT workflow not seeded in database.")

    db_dfa = DFAEngine.from_db_workflow(workflow)

    # 1. State and alphabet checks
    assert db_dfa.initial_state == "ORDER_CREATED"
    assert "ORDER_CONFIRMED" in db_dfa.accepting_states
    assert "ORDER_CANCELLED" in db_dfa.accepting_states
    assert len(db_dfa.states) >= 6

    # 2. Trace execution comparison with in-memory DFA
    in_memory_dfa = get_online_payment_dfa()

    valid_events = ["INITIATE_PAYMENT", "VERIFY_PAYMENT", "PAYMENT_SUCCESS"]
    db_res = db_dfa.validate_trace(valid_events)
    mem_res = in_memory_dfa.validate_trace(valid_events)

    assert db_res.is_valid is True
    assert db_res.final_state == mem_res.final_state
    assert db_res.visited_states == mem_res.visited_states

    # 3. Invalid transition comparison
    invalid_events = ["INITIATE_PAYMENT", "PAYMENT_SUCCESS"]  # Skip verification
    db_inv = db_dfa.validate_trace(invalid_events)
    mem_inv = in_memory_dfa.validate_trace(invalid_events)

    assert db_inv.is_valid is False
    assert db_inv.final_state == mem_inv.final_state
    assert db_inv.error_type == mem_inv.error_type
