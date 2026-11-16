"""API integration tests for WorkflowGuard REST endpoints."""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify root endpoint returns API links and documentation paths."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "WorkflowGuard"
    assert "/docs" in data["documentation"]
    assert "/api/v1" in data["api_v1"]


def test_health_endpoint():
    """Verify health check endpoint returns database and ML engine status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("operational", "degraded")
    assert "database" in data
    assert "ml_engine" in data


def test_list_workflows():
    """Verify workflows list returns registered workflow definitions."""
    response = client.get("/api/v1/workflows")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    codes = [w["code"] for w in data]
    assert "ONLINE_PAYMENT" in codes


def test_get_workflow_by_code():
    """Verify fetching single workflow by code returns states and transitions."""
    response = client.get("/api/v1/workflows/ONLINE_PAYMENT")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "ONLINE_PAYMENT"
    assert len(data["states"]) >= 6
    assert len(data["transitions"]) >= 8


def test_get_workflow_not_found():
    """Verify 404 response for non-existent workflow identifier."""
    response = client.get("/api/v1/workflows/UNKNOWN_WORKFLOW_XYZ")
    assert response.status_code == 404


def test_case_lifecycle_and_event_submission():
    """End-to-end test: Create case -> Step through events -> Verify state updates."""
    custom_case_id = f"TEST-API-{uuid.uuid4().hex[:6].upper()}"

    # 1. Create Case
    create_resp = client.post(
        "/api/v1/cases",
        json={
            "workflow_code": "ONLINE_PAYMENT",
            "case_id": custom_case_id,
            "total_amount": 129.50,
            "user_id": "test_user_42",
        },
    )
    assert create_resp.status_code == 201
    case_data = create_resp.json()
    assert case_data["case_id"] == custom_case_id
    assert case_data["current_state_key"] == "ORDER_CREATED"
    assert case_data["status"] == "RUNNING"

    # 2. Submit Event 1: INITIATE_PAYMENT
    ev1_resp = client.post(
        f"/api/v1/cases/{custom_case_id}/events",
        json={
            "event_name": "INITIATE_PAYMENT",
            "execution_duration_ms": 1200,
        },
    )
    assert ev1_resp.status_code == 200
    ev1_data = ev1_resp.json()
    assert ev1_data["current_state"] == "PAYMENT_INITIATED"
    assert ev1_data["status"] == "RUNNING"
    assert ev1_data["evaluation"]["classification"] == "NORMAL"

    # 3. Submit Event 2: VERIFY_PAYMENT
    ev2_resp = client.post(
        f"/api/v1/cases/{custom_case_id}/events",
        json={
            "event_name": "VERIFY_PAYMENT",
            "execution_duration_ms": 1100,
        },
    )
    assert ev2_resp.status_code == 200
    ev2_data = ev2_resp.json()
    assert ev2_data["current_state"] == "PAYMENT_VERIFYING"

    # 4. Submit Event 3: PAYMENT_SUCCESS (Terminal State)
    ev3_resp = client.post(
        f"/api/v1/cases/{custom_case_id}/events",
        json={
            "event_name": "PAYMENT_SUCCESS",
            "execution_duration_ms": 900,
        },
    )
    assert ev3_resp.status_code == 200
    ev3_data = ev3_resp.json()
    assert ev3_data["current_state"] == "ORDER_CONFIRMED"
    assert ev3_data["status"] == "COMPLETED"


def test_syntactic_violation_records_anomaly():
    """Verify that an illegal transition flags the case as ANOMALOUS and stores anomaly record."""
    bad_case_id = f"TEST-ANOM-{uuid.uuid4().hex[:6].upper()}"

    # Create Case
    client.post(
        "/api/v1/cases",
        json={
            "workflow_code": "ONLINE_PAYMENT",
            "case_id": bad_case_id,
            "total_amount": 50.00,
        },
    )

    # Immediately attempt PAYMENT_SUCCESS from ORDER_CREATED (Illegal!)
    ev_resp = client.post(
        f"/api/v1/cases/{bad_case_id}/events",
        json={
            "event_name": "PAYMENT_SUCCESS",
            "execution_duration_ms": 1000,
        },
    )
    assert ev_resp.status_code == 200
    data = ev_resp.json()
    assert data["status"] == "ANOMALOUS"
    assert data["current_state"] == "TRAP_STATE"
    assert data["evaluation"]["is_anomaly"] is True

    # Check that anomaly appears in /cases/{case_id}/anomalies
    anom_resp = client.get(f"/api/v1/cases/{bad_case_id}/anomalies")
    assert anom_resp.status_code == 200
    anomalies = anom_resp.json()
    assert len(anomalies) >= 1
    assert anomalies[0]["case_id"] == bad_case_id
    assert anomalies[0]["is_anomaly"] is True


def test_paginated_anomalies_list():
    """Verify /api/v1/anomalies returns paginated structure."""
    response = client.get("/api/v1/anomalies?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data


def test_batch_simulation_endpoint():
    """Verify /api/v1/simulation/run-batch evaluates multiple traces in a single request."""
    batch_payload = {
        "workflow_code": "ONLINE_PAYMENT",
        "cases": [
            {
                "case_id": "SIM-NORMAL-01",
                "total_amount": 75.00,
                "events": [
                    {"event_name": "INITIATE_PAYMENT", "execution_duration_ms": 1000},
                    {"event_name": "VERIFY_PAYMENT", "execution_duration_ms": 1000},
                    {"event_name": "PAYMENT_SUCCESS", "execution_duration_ms": 800},
                ],
            },
            {
                "case_id": "SIM-ANOM-01",
                "total_amount": 99999.00,  # Extreme amount
                "events": [
                    {"event_name": "INITIATE_PAYMENT", "execution_duration_ms": 1000},
                    {"event_name": "VERIFY_PAYMENT", "execution_duration_ms": 1000},
                    {"event_name": "PAYMENT_SUCCESS", "execution_duration_ms": 800},
                ],
            },
            {
                "case_id": "SIM-SYNTACTIC-01",
                "total_amount": 40.00,
                "events": [
                    {"event_name": "PAYMENT_SUCCESS", "execution_duration_ms": 500},  # Direct confirm
                ],
            },
        ],
    }

    response = client.post("/api/v1/simulation/run-batch", json=batch_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_cases"] == 3
    assert data["processed_count"] == 3
    assert data["anomalies_detected"] >= 2
    assert len(data["results"]) == 3


def test_idempotent_event_submission():
    """Verify submitting an event with identical idempotency_key returns cached result."""
    case_id = f"TEST-IDEM-{uuid.uuid4().hex[:6].upper()}"
    client.post("/api/v1/cases", json={"case_id": case_id, "total_amount": 50.00})

    req_payload = {
        "event_name": "INITIATE_PAYMENT",
        "execution_duration_ms": 1200,
        "idempotency_key": "IDEM-KEY-XYZ-123",
    }

    # First attempt
    res1 = client.post(f"/api/v1/cases/{case_id}/events", json=req_payload)
    assert res1.status_code == 200

    # Duplicate attempt
    res2 = client.post(f"/api/v1/cases/{case_id}/events", json=req_payload)
    assert res2.status_code == 200
    assert res2.json()["evaluation"].get("idempotent_replay") is True
