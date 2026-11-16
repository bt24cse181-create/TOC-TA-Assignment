"""Unit tests verifying SQLAlchemy model schemas against database/schema.sql requirements."""

from sqlalchemy.orm import configure_mappers
from app.models import (
    AnomalyResult,
    AnomalySeverityEnum,
    Base,
    CaseStatusEnum,
    DetectorTypeEnum,
    EventLog,
    ProcessCase,
    StateTypeEnum,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)


def test_mapper_initialization():
    """Verify that all ORM models and relationships configure without errors."""
    configure_mappers()


def test_table_names_match_schema():
    """Verify that ORM model table names match schema.sql exactly."""
    expected_tables = {
        "workflows",
        "workflow_states",
        "workflow_transitions",
        "process_cases",
        "event_logs",
        "anomaly_results",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables == actual_tables, f"Mismatch: expected {expected_tables}, got {actual_tables}"


def test_workflows_columns():
    """Verify columns and constraints on Workflow model."""
    table = Base.metadata.tables["workflows"]
    columns = set(table.columns.keys())
    expected = {"id", "code", "name", "description", "version", "is_active", "created_at", "updated_at"}
    assert expected.issubset(columns)
    assert table.columns["code"].unique is True


def test_workflow_states_columns_and_constraints():
    """Verify columns and unique constraints on WorkflowState model."""
    table = Base.metadata.tables["workflow_states"]
    columns = set(table.columns.keys())
    expected = {
        "id",
        "workflow_id",
        "state_key",
        "state_name",
        "state_type",
        "description",
        "is_initial",
        "is_terminal",
        "created_at",
    }
    assert expected.issubset(columns)

    # Verify unique constraint on (workflow_id, state_key)
    uq_names = [uq.name for uq in table.constraints if hasattr(uq, "columns")]
    assert "uq_workflow_state" in uq_names


def test_workflow_transitions_columns_and_constraints():
    """Verify columns and unique constraints on WorkflowTransition model."""
    table = Base.metadata.tables["workflow_transitions"]
    columns = set(table.columns.keys())
    expected = {
        "id",
        "workflow_id",
        "from_state_id",
        "to_state_id",
        "event_name",
        "is_allowed",
        "max_retries",
        "condition_meta",
        "created_at",
    }
    assert expected.issubset(columns)

    uq_names = [uq.name for uq in table.constraints if hasattr(uq, "columns")]
    assert "uq_state_event" in uq_names


def test_process_cases_columns():
    """Verify columns on ProcessCase model."""
    table = Base.metadata.tables["process_cases"]
    columns = set(table.columns.keys())
    expected = {
        "id",
        "case_id",
        "workflow_id",
        "current_state_id",
        "status",
        "total_amount",
        "user_id",
        "retry_count",
        "started_at",
        "completed_at",
        "metadata_json",
    }
    assert expected.issubset(columns)
    assert table.columns["case_id"].unique is True


def test_event_logs_columns():
    """Verify columns on EventLog model."""
    table = Base.metadata.tables["event_logs"]
    columns = set(table.columns.keys())
    expected = {
        "id",
        "case_id",
        "workflow_id",
        "event_name",
        "from_state_key",
        "to_state_key",
        "timestamp",
        "execution_duration_ms",
        "retry_count",
        "payload_json",
    }
    assert expected.issubset(columns)


def test_anomaly_results_columns():
    """Verify columns on AnomalyResult model."""
    table = Base.metadata.tables["anomaly_results"]
    columns = set(table.columns.keys())
    expected = {
        "id",
        "case_id",
        "event_log_id",
        "detector_type",
        "is_anomaly",
        "anomaly_score",
        "anomaly_reason",
        "severity",
        "rule_violation",
        "detected_at",
        "details_json",
    }
    assert expected.issubset(columns)


def test_enum_values():
    """Verify enum members match specification in schema.sql."""
    assert set(StateTypeEnum._member_names_) == {"START", "INTERMEDIATE", "TERMINAL_SUCCESS", "TERMINAL_FAILURE", "ERROR"}
    assert set(CaseStatusEnum._member_names_) == {"RUNNING", "COMPLETED", "FAILED", "ANOMALOUS"}
    assert set(DetectorTypeEnum._member_names_) == {"DFA", "ISOLATION_FOREST", "HYBRID"}
    assert set(AnomalySeverityEnum._member_names_) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
