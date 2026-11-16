"""Unit test suite for DFA Workflow Engine (Theory of Computation Core).

Validates formal DFA behavior, bounded retry enforcement, reachability,
dead-end analysis, and error classification completely in-memory without a
database dependency.
"""

import pytest
from app.engine.dfa_engine import (
    DFAEngine,
    DFAErrorType,
    DFAState,
    DFATransition,
    WorkflowDefinitionError,
    get_online_payment_dfa,
)


@pytest.fixture
def payment_dfa() -> DFAEngine:
    """Fixture providing standard Online Payment Processing DFA."""
    return get_online_payment_dfa()


# ----------------------------------------------------------------------
# 1. Valid Workflow Traces
# ----------------------------------------------------------------------

def test_valid_payment_confirmation(payment_dfa: DFAEngine):
    """Happy path: Order created -> Initiated -> Verifying -> Confirmed."""
    events = [
        "INITIATE_PAYMENT",
        "VERIFY_PAYMENT",
        "PAYMENT_SUCCESS",
    ]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is True
    assert res.is_completed is True
    assert res.is_partial is False
    assert res.final_state == "ORDER_CONFIRMED"
    assert res.visited_states == [
        "ORDER_CREATED",
        "PAYMENT_INITIATED",
        "PAYMENT_VERIFYING",
        "ORDER_CONFIRMED",
    ]
    assert res.first_invalid_event is None


def test_order_cancellation_from_created(payment_dfa: DFAEngine):
    """Customer cancels immediately after creating order."""
    events = ["CANCEL_ORDER"]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is True
    assert res.is_completed is True
    assert res.final_state == "ORDER_CANCELLED"
    assert res.visited_states == ["ORDER_CREATED", "ORDER_CANCELLED"]


def test_order_cancellation_from_initiated(payment_dfa: DFAEngine):
    """Customer cancels after initiating payment."""
    events = ["INITIATE_PAYMENT", "CANCEL_ORDER"]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is True
    assert res.is_completed is True
    assert res.final_state == "ORDER_CANCELLED"
    assert res.visited_states == [
        "ORDER_CREATED",
        "PAYMENT_INITIATED",
        "ORDER_CANCELLED",
    ]


def test_failure_and_single_permitted_retry(payment_dfa: DFAEngine):
    """Payment fails once, retried successfully, then confirmed."""
    events = [
        "INITIATE_PAYMENT",
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",   # In PAYMENT_FAILED (retry_count = 0)
        "RETRY_PAYMENT",     # Back to PAYMENT_INITIATED (retry_count = 1)
        "VERIFY_PAYMENT",
        "PAYMENT_SUCCESS",   # ORDER_CONFIRMED
    ]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is True
    assert res.is_completed is True
    assert res.final_state == "ORDER_CONFIRMED"
    assert res.final_retry_count == 1
    assert res.visited_states == [
        "ORDER_CREATED",
        "PAYMENT_INITIATED",
        "PAYMENT_VERIFYING",
        "PAYMENT_FAILED",
        "PAYMENT_INITIATED",
        "PAYMENT_VERIFYING",
        "ORDER_CONFIRMED",
    ]


def test_multiple_retries_up_to_limit(payment_dfa: DFAEngine):
    """Exactly 3 retries executed (the configured limit), followed by success."""
    events = [
        "INITIATE_PAYMENT",
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",  # Failed attempt 1
        "RETRY_PAYMENT",    # Retry 1 (count: 1)
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",  # Failed attempt 2
        "RETRY_PAYMENT",    # Retry 2 (count: 2)
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",  # Failed attempt 3
        "RETRY_PAYMENT",    # Retry 3 (count: 3)
        "VERIFY_PAYMENT",
        "PAYMENT_SUCCESS",  # Final attempt succeeds
    ]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is True
    assert res.is_completed is True
    assert res.final_state == "ORDER_CONFIRMED"
    assert res.final_retry_count == 3


def test_retry_exhaustion_valid_cancellation(payment_dfa: DFAEngine):
    """After 3 failed attempts, EXCEED_MAX_RETRIES is triggered to cancel order."""
    events = [
        "INITIATE_PAYMENT",
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",
        "RETRY_PAYMENT",    # count = 1
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",
        "RETRY_PAYMENT",    # count = 2
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",
        "RETRY_PAYMENT",    # count = 3
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",  # now in PAYMENT_FAILED with count = 3
        "EXCEED_MAX_RETRIES",
    ]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is True
    assert res.is_completed is True
    assert res.final_state == "ORDER_CANCELLED"


# ----------------------------------------------------------------------
# 2. Retry Violations & Guard Conditions
# ----------------------------------------------------------------------

def test_retry_limit_exceeded_rejection(payment_dfa: DFAEngine):
    """Attempting a 4th retry when limit is 3 must transition to TRAP_STATE."""
    events = [
        "INITIATE_PAYMENT",
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",
        "RETRY_PAYMENT",    # 1
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",
        "RETRY_PAYMENT",    # 2
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",
        "RETRY_PAYMENT",    # 3 (limit reached)
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",
        "RETRY_PAYMENT",    # 4 (VIOLATION!)
    ]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is False
    assert res.final_state == DFAEngine.TRAP_STATE
    assert res.first_invalid_event == "RETRY_PAYMENT"
    assert res.first_invalid_state == "PAYMENT_FAILED"
    assert res.error_type == DFAErrorType.RETRY_LIMIT_EXCEEDED
    assert "Maximum retry limit (3) exceeded" in (res.error_message or "")


def test_premature_exceed_max_retries_rejected(payment_dfa: DFAEngine):
    """Cannot fire EXCEED_MAX_RETRIES before exhausting retries."""
    events = [
        "INITIATE_PAYMENT",
        "VERIFY_PAYMENT",
        "PAYMENT_FAILURE",
        "EXCEED_MAX_RETRIES",  # count is 0, but required is >= 3
    ]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is False
    assert res.final_state == DFAEngine.TRAP_STATE
    assert res.error_type == DFAErrorType.GUARD_CONDITION_FAILED
    assert "Cannot trigger EXCEED_MAX_RETRIES" in (res.error_message or "")


# ----------------------------------------------------------------------
# 3. Syntactic Skips & Illegal Transitions
# ----------------------------------------------------------------------

def test_confirmation_before_verification_rejected(payment_dfa: DFAEngine):
    """Attacker attempts to skip verification directly to confirmation."""
    events = [
        "INITIATE_PAYMENT",
        "PAYMENT_SUCCESS",  # Invalid from PAYMENT_INITIATED!
    ]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is False
    assert res.final_state == DFAEngine.TRAP_STATE
    assert res.first_invalid_event == "PAYMENT_SUCCESS"
    assert res.first_invalid_state == "PAYMENT_INITIATED"
    assert res.first_invalid_index == 1
    assert res.error_type == DFAErrorType.ILLEGAL_TRANSITION


def test_skip_from_created_to_confirmation(payment_dfa: DFAEngine):
    """Skipping all payment steps from ORDER_CREATED to PAYMENT_SUCCESS."""
    events = ["PAYMENT_SUCCESS"]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is False
    assert res.final_state == DFAEngine.TRAP_STATE
    assert res.first_invalid_event == "PAYMENT_SUCCESS"
    assert res.first_invalid_state == "ORDER_CREATED"
    assert res.first_invalid_index == 0


def test_cancellation_followed_by_confirmation_rejected(payment_dfa: DFAEngine):
    """Terminal state violation: Once cancelled, cannot be confirmed."""
    events = ["CANCEL_ORDER", "PAYMENT_SUCCESS"]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is False
    assert res.final_state == DFAEngine.TRAP_STATE
    assert res.first_invalid_event == "PAYMENT_SUCCESS"
    assert res.first_invalid_state == "ORDER_CANCELLED"
    assert res.first_invalid_index == 1
    assert res.error_type == DFAErrorType.TERMINAL_STATE_VIOLATION


def test_transition_from_confirmed_terminal_state_rejected(payment_dfa: DFAEngine):
    """Terminal state violation: No transitions allowed out of ORDER_CONFIRMED."""
    events = [
        "INITIATE_PAYMENT",
        "VERIFY_PAYMENT",
        "PAYMENT_SUCCESS",
        "INITIATE_PAYMENT",  # Attempting to re-initiate after confirmation
    ]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is False
    assert res.final_state == DFAEngine.TRAP_STATE
    assert res.first_invalid_state == "ORDER_CONFIRMED"
    assert res.error_type == DFAErrorType.TERMINAL_STATE_VIOLATION


# ----------------------------------------------------------------------
# 4. Unknown Events & Incomplete Traces
# ----------------------------------------------------------------------

def test_unknown_event_handled_safely(payment_dfa: DFAEngine):
    """Unrecognized event symbols are rejected with UNKNOWN_EVENT."""
    events = ["HACK_BYPASS_SECURITY"]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is False
    assert res.final_state == DFAEngine.TRAP_STATE
    assert res.first_invalid_event == "HACK_BYPASS_SECURITY"
    assert res.error_type == DFAErrorType.UNKNOWN_EVENT


def test_partial_execution_not_treated_as_anomalous(payment_dfa: DFAEngine):
    """In-progress trace that is valid so far must be marked valid and partial."""
    events = ["INITIATE_PAYMENT"]
    res = payment_dfa.validate_trace(events)
    assert res.is_valid is True
    assert res.is_completed is False
    assert res.is_partial is True
    assert res.final_state == "PAYMENT_INITIATED"


def test_empty_trace_is_valid_partial(payment_dfa: DFAEngine):
    """Empty event sequence rests at initial state without errors."""
    res = payment_dfa.validate_trace([])
    assert res.is_valid is True
    assert res.is_completed is False
    assert res.is_partial is True
    assert res.final_state == "ORDER_CREATED"
    assert res.visited_states == ["ORDER_CREATED"]


# ----------------------------------------------------------------------
# 5. Graph Reachability & Dead-End Analysis
# ----------------------------------------------------------------------

def test_all_operational_states_reachable(payment_dfa: DFAEngine):
    """All non-trap operational states are reachable from ORDER_CREATED."""
    reachable = payment_dfa.get_reachable_states()
    expected_operational = {
        "ORDER_CREATED",
        "PAYMENT_INITIATED",
        "PAYMENT_VERIFYING",
        "PAYMENT_FAILED",
        "ORDER_CONFIRMED",
        "ORDER_CANCELLED",
    }
    assert expected_operational.issubset(reachable)


def test_unreachable_state_detection():
    """Engine detects states defined in Q that cannot be reached from q0."""
    engine = DFAEngine(
        states={
            "S0": DFAState(key="S0", name="Start", is_initial=True),
            "S1": DFAState(key="S1", name="Step 1"),
            "ORPHAN": DFAState(key="ORPHAN", name="Unreachable"),
        },
        alphabet={"E1"},
        initial_state="S0",
        transitions={
            ("S0", "E1"): DFATransition(from_state="S0", event="E1", to_state="S1"),
        },
        accepting_states={"S1"},
        workflow_code="ORPHAN_TEST",
    )
    unreachable = engine.get_unreachable_states()
    assert unreachable == {"ORPHAN"}


def test_dead_end_state_detection():
    """Identifies non-terminal intermediate states that have no outgoing transitions."""
    engine = DFAEngine(
        states={
            "S0": DFAState(key="S0", name="Start", is_initial=True),
            "STUCK": DFAState(key="STUCK", name="Stuck", is_terminal=False),
            "END": DFAState(key="END", name="End", is_terminal=True),
        },
        alphabet={"GO_STUCK", "GO_END"},
        initial_state="S0",
        transitions={
            ("S0", "GO_STUCK"): DFATransition(from_state="S0", event="GO_STUCK", to_state="STUCK"),
            ("S0", "GO_END"): DFATransition(from_state="S0", event="GO_END", to_state="END"),
        },
        accepting_states={"END"},
        workflow_code="DEAD_END_TEST",
    )
    dead_ends = engine.get_dead_end_states()
    assert dead_ends == {"STUCK"}


# ----------------------------------------------------------------------
# 6. Malformed Definition Checks
# ----------------------------------------------------------------------

def test_malformed_definition_missing_initial_state():
    """DFA definition without initial state raises WorkflowDefinitionError."""
    with pytest.raises(WorkflowDefinitionError) as exc_info:
        DFAEngine(
            states={"S1": DFAState(key="S1", name="S1")},
            alphabet={"E1"},
            initial_state="NON_EXISTENT",
            transitions={},
            accepting_states={"S1"},
        )
    assert "Initial state 'NON_EXISTENT' is not in states Q" in str(exc_info.value)


def test_malformed_definition_invalid_transition_state():
    """Transition referencing a state not in Q raises WorkflowDefinitionError."""
    with pytest.raises(WorkflowDefinitionError) as exc_info:
        DFAEngine(
            states={"S0": DFAState(key="S0", name="S0", is_initial=True)},
            alphabet={"E1"},
            initial_state="S0",
            transitions={
                ("S0", "E1"): DFATransition(from_state="S0", event="E1", to_state="UNKNOWN_TARGET"),
            },
            accepting_states=set(),
        )
    assert "Transition to_state 'UNKNOWN_TARGET' is not in states Q" in str(exc_info.value)


def test_malformed_definition_event_not_in_alphabet():
    """Transition event not defined in alphabet Sigma raises WorkflowDefinitionError."""
    with pytest.raises(WorkflowDefinitionError) as exc_info:
        DFAEngine(
            states={"S0": DFAState(key="S0", name="S0", is_initial=True)},
            alphabet={"ALLOWED_EVENT"},
            initial_state="S0",
            transitions={
                ("S0", "ROGUE_EVENT"): DFATransition(from_state="S0", event="ROGUE_EVENT", to_state="S0"),
            },
            accepting_states=set(),
        )
    assert "Transition event 'ROGUE_EVENT' is not in alphabet Sigma" in str(exc_info.value)
