"""Unit tests for Hybrid Decision Engine (Phase 4)."""

import pytest

from app.engine.dfa_engine import DFAErrorType, get_online_payment_dfa
from app.engine.hybrid_engine import (
    HybridClassification,
    HybridEngine,
    HybridEvaluationResult,
)
from app.engine.ml_engine import MLEngine
from app.models.anomaly import AnomalySeverityEnum


@pytest.fixture
def hybrid_engine() -> HybridEngine:
    """Fixture providing a default HybridEngine instance with loaded ML weights."""
    return HybridEngine.default()


# ----------------------------------------------------------------------
# 1. Four Canonical Classifications
# ----------------------------------------------------------------------

def test_hybrid_classification_normal(hybrid_engine: HybridEngine):
    """DFA Valid + ML Normal -> NORMAL."""
    case = {
        "case_id": "TEST-NORMAL-01",
        "total_amount": 85.00,
        "events": [
            {"event_name": "INITIATE_PAYMENT", "from_state": "ORDER_CREATED", "to_state": "PAYMENT_INITIATED", "execution_duration_ms": 1200, "inter_event_delay_ms": 500},
            {"event_name": "VERIFY_PAYMENT", "from_state": "PAYMENT_INITIATED", "to_state": "PAYMENT_VERIFYING", "execution_duration_ms": 1100, "inter_event_delay_ms": 400},
            {"event_name": "PAYMENT_SUCCESS", "from_state": "PAYMENT_VERIFYING", "to_state": "ORDER_CONFIRMED", "execution_duration_ms": 900, "inter_event_delay_ms": 0},
        ],
    }
    res = hybrid_engine.evaluate_case(case)
    assert res.classification == HybridClassification.NORMAL
    assert res.is_anomaly is False
    assert res.dfa_is_valid is True
    assert res.ml_is_anomaly is False
    assert res.is_completed is True
    assert res.severity == AnomalySeverityEnum.LOW
    assert "conforms to both DFA rules" in res.explanation


def test_hybrid_classification_behavioral_anomaly(hybrid_engine: HybridEngine):
    """DFA Valid + ML Outlier (e.g. Extreme Amount) -> BEHAVIORAL_ANOMALY."""
    case = {
        "case_id": "TEST-BEH-01",
        "total_amount": 95000.00,  # Extreme outlier amount
        "events": [
            {"event_name": "INITIATE_PAYMENT", "from_state": "ORDER_CREATED", "to_state": "PAYMENT_INITIATED", "execution_duration_ms": 1200, "inter_event_delay_ms": 500},
            {"event_name": "VERIFY_PAYMENT", "from_state": "PAYMENT_INITIATED", "to_state": "PAYMENT_VERIFYING", "execution_duration_ms": 1100, "inter_event_delay_ms": 400},
            {"event_name": "PAYMENT_SUCCESS", "from_state": "PAYMENT_VERIFYING", "to_state": "ORDER_CONFIRMED", "execution_duration_ms": 900, "inter_event_delay_ms": 0},
        ],
    }
    res = hybrid_engine.evaluate_case(case)
    assert res.dfa_is_valid is True
    assert res.ml_is_anomaly is True
    assert res.classification == HybridClassification.BEHAVIORAL_ANOMALY
    assert res.is_anomaly is True
    assert res.severity in (AnomalySeverityEnum.MEDIUM, AnomalySeverityEnum.HIGH)
    assert "statistical outlier" in res.explanation.lower()


def test_hybrid_classification_syntactic_anomaly(hybrid_engine: HybridEngine):
    """DFA Invalid (Illegal Skip) + ML Normal -> SYNTACTIC_ANOMALY."""
    # An invalid transition executed at completely normal human speeds & amounts
    case = {
        "case_id": "TEST-SYNTACTIC-01",
        "total_amount": 50.00,
        "events": [
            {"event_name": "INITIATE_PAYMENT", "from_state": "ORDER_CREATED", "to_state": "PAYMENT_INITIATED", "execution_duration_ms": 1200, "inter_event_delay_ms": 500},
            {"event_name": "PAYMENT_SUCCESS", "from_state": "PAYMENT_INITIATED", "to_state": "TRAP_STATE", "execution_duration_ms": 1100, "inter_event_delay_ms": 400},
        ],
    }
    # Force ML to report normal by using high threshold
    res = hybrid_engine.evaluate_case(case, custom_threshold=0.99)
    assert res.dfa_is_valid is False
    assert res.ml_is_anomaly is False
    assert res.classification == HybridClassification.SYNTACTIC_ANOMALY
    assert res.is_anomaly is True
    assert res.dfa_error_type == DFAErrorType.ILLEGAL_TRANSITION
    assert res.severity == AnomalySeverityEnum.HIGH
    assert "DFA grammar violation" in res.explanation


def test_hybrid_classification_compound_anomaly(hybrid_engine: HybridEngine):
    """DFA Invalid + ML Outlier (e.g. Bot Speed + Illegal Skip) -> COMPOUND_ANOMALY."""
    case = {
        "case_id": "TEST-COMPOUND-01",
        "total_amount": 80000.00,  # Outlier amount
        "events": [
            {"event_name": "PAYMENT_SUCCESS", "from_state": "ORDER_CREATED", "to_state": "TRAP_STATE", "execution_duration_ms": 5, "inter_event_delay_ms": 2},
        ],
    }
    res = hybrid_engine.evaluate_case(case)
    assert res.dfa_is_valid is False
    assert res.ml_is_anomaly is True
    assert res.classification == HybridClassification.COMPOUND_ANOMALY
    assert res.is_anomaly is True
    assert res.severity == AnomalySeverityEnum.CRITICAL
    assert "Compound anomaly" in res.explanation


# ----------------------------------------------------------------------
# 2. Incomplete Traces & Partial Status
# ----------------------------------------------------------------------

def test_incomplete_trace_not_automatically_anomalous(hybrid_engine: HybridEngine):
    """Valid in-progress executions must be classified as NORMAL with is_partial=True."""
    case = {
        "case_id": "TEST-PARTIAL-01",
        "total_amount": 45.00,
        "events": [
            {"event_name": "INITIATE_PAYMENT", "from_state": "ORDER_CREATED", "to_state": "PAYMENT_INITIATED", "execution_duration_ms": 1200, "inter_event_delay_ms": 400},
        ],
    }
    res = hybrid_engine.evaluate_case(case)
    assert res.dfa_is_valid is True
    assert res.is_completed is False
    assert res.is_partial is True
    assert res.classification == HybridClassification.NORMAL
    assert res.is_anomaly is False
    assert "in-progress" in res.explanation.lower()


def test_retry_limit_violation_in_hybrid(hybrid_engine: HybridEngine):
    """Attempting a 4th retry causes syntactic rejection in the hybrid result."""
    case = {
        "case_id": "TEST-RETRY-LIMIT-01",
        "total_amount": 60.00,
        "events": [
            {"event_name": "INITIATE_PAYMENT", "from_state": "ORDER_CREATED", "to_state": "PAYMENT_INITIATED", "execution_duration_ms": 800},
            {"event_name": "VERIFY_PAYMENT", "from_state": "PAYMENT_INITIATED", "to_state": "PAYMENT_VERIFYING", "execution_duration_ms": 800},
            {"event_name": "PAYMENT_FAILURE", "from_state": "PAYMENT_VERIFYING", "to_state": "PAYMENT_FAILED", "execution_duration_ms": 800},
            {"event_name": "RETRY_PAYMENT", "from_state": "PAYMENT_FAILED", "to_state": "PAYMENT_INITIATED", "execution_duration_ms": 800},  # 1
            {"event_name": "VERIFY_PAYMENT", "from_state": "PAYMENT_INITIATED", "to_state": "PAYMENT_VERIFYING", "execution_duration_ms": 800},
            {"event_name": "PAYMENT_FAILURE", "from_state": "PAYMENT_VERIFYING", "to_state": "PAYMENT_FAILED", "execution_duration_ms": 800},
            {"event_name": "RETRY_PAYMENT", "from_state": "PAYMENT_FAILED", "to_state": "PAYMENT_INITIATED", "execution_duration_ms": 800},  # 2
            {"event_name": "VERIFY_PAYMENT", "from_state": "PAYMENT_INITIATED", "to_state": "PAYMENT_VERIFYING", "execution_duration_ms": 800},
            {"event_name": "PAYMENT_FAILURE", "from_state": "PAYMENT_VERIFYING", "to_state": "PAYMENT_FAILED", "execution_duration_ms": 800},
            {"event_name": "RETRY_PAYMENT", "from_state": "PAYMENT_FAILED", "to_state": "PAYMENT_INITIATED", "execution_duration_ms": 800},  # 3
            {"event_name": "VERIFY_PAYMENT", "from_state": "PAYMENT_INITIATED", "to_state": "PAYMENT_VERIFYING", "execution_duration_ms": 800},
            {"event_name": "PAYMENT_FAILURE", "from_state": "PAYMENT_VERIFYING", "to_state": "PAYMENT_FAILED", "execution_duration_ms": 800},
            {"event_name": "RETRY_PAYMENT", "from_state": "PAYMENT_FAILED", "to_state": "TRAP_STATE", "execution_duration_ms": 800},  # 4: EXCEEDED!
        ],
    }
    res = hybrid_engine.evaluate_case(case)
    assert res.dfa_is_valid is False
    assert res.dfa_error_type == DFAErrorType.RETRY_LIMIT_EXCEEDED
    assert res.is_anomaly is True


def test_hybrid_engine_graceful_when_ml_missing():
    """Engine functions strictly on DFA rules if ML model is unavailable."""
    engine_no_ml = HybridEngine(dfa_engine=get_online_payment_dfa(), ml_engine=None)
    case = {
        "case_id": "TEST-NO-ML-01",
        "total_amount": 50.00,
        "events": [
            {"event_name": "INITIATE_PAYMENT", "execution_duration_ms": 1000},
            {"event_name": "VERIFY_PAYMENT", "execution_duration_ms": 1000},
            {"event_name": "PAYMENT_SUCCESS", "execution_duration_ms": 1000},
        ],
    }
    res = engine_no_ml.evaluate_case(case)
    assert res.dfa_is_valid is True
    assert res.classification == HybridClassification.NORMAL
    assert res.model_version == "Unavailable"
