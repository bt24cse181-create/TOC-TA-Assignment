"""Unit tests for FeatureExtractor (Feature Engineering Pipeline)."""

import numpy as np
import pandas as pd
import pytest

from app.engine.feature_extractor import FEATURE_COLUMNS, FeatureExtractor


def test_feature_columns_definition():
    """Verify that FEATURE_COLUMNS is an immutable sequence of unique column names."""
    assert len(FEATURE_COLUMNS) == 20
    assert len(set(FEATURE_COLUMNS)) == len(FEATURE_COLUMNS)
    assert "amount" in FEATURE_COLUMNS
    assert "log_amount" in FEATURE_COLUMNS
    assert "total_duration_ms" in FEATURE_COLUMNS


def test_no_identifiers_or_labels_in_features():
    """Verify that no ground-truth labels or IDs leak into the feature space."""
    forbidden = {"case_id", "user_id", "is_anomaly", "anomaly_category", "label", "final_state"}
    features_set = set(FEATURE_COLUMNS)
    overlap = features_set.intersection(forbidden)
    assert not overlap, f"Forbidden leakage fields found in feature columns: {overlap}"


def test_extract_features_normal_case():
    """Verify feature extraction for a standard happy path execution case."""
    case = {
        "case_id": "CASE-TEST-001",
        "total_amount": 150.00,
        "total_duration_ms": 3200,
        "retry_count": 0,
        "failure_count": 0,
        "events": [
            {
                "event_name": "INITIATE_PAYMENT",
                "from_state": "ORDER_CREATED",
                "to_state": "PAYMENT_INITIATED",
                "execution_duration_ms": 1000,
                "inter_event_delay_ms": 100,
            },
            {
                "event_name": "VERIFY_PAYMENT",
                "from_state": "PAYMENT_INITIATED",
                "to_state": "PAYMENT_VERIFYING",
                "execution_duration_ms": 1100,
                "inter_event_delay_ms": 200,
            },
            {
                "event_name": "PAYMENT_SUCCESS",
                "from_state": "PAYMENT_VERIFYING",
                "to_state": "ORDER_CONFIRMED",
                "execution_duration_ms": 800,
                "inter_event_delay_ms": 0,
            },
        ],
    }

    feat = FeatureExtractor.extract_features(case)
    assert feat["amount"] == 150.00
    assert feat["event_count"] == 3.0
    assert feat["retry_count"] == 0.0
    assert feat["failure_count"] == 0.0
    assert feat["freq_initiate_payment"] == 1.0
    assert feat["freq_verify_payment"] == 1.0
    assert feat["speed_anomaly_flag"] == 0.0
    assert feat["mean_step_duration_ms"] == pytest.approx(966.67, rel=1e-2)


def test_extract_vector_shape_and_order():
    """Verify vector extraction outputs 1D NumPy array matching FEATURE_COLUMNS order."""
    case = {"total_amount": 75.50, "events": []}
    vec = FeatureExtractor.extract_vector(case)
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (len(FEATURE_COLUMNS),)
    assert vec.dtype == np.float64
    assert vec[0] == 75.50  # First column is amount


def test_extract_batch_dataframe():
    """Verify batch extraction into Pandas DataFrame."""
    cases = [
        {"total_amount": 10.0, "events": []},
        {"total_amount": 25.0, "events": []},
        {"total_amount": 100.0, "events": []},
    ]
    df = FeatureExtractor.extract_batch(cases)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == list(FEATURE_COLUMNS)
    assert len(df) == 3
    assert not df.isna().any().any()


def test_missing_and_malformed_inputs_handled_safely():
    """Verify that None values, missing keys, and invalid types don't raise exceptions."""
    malformed_cases = [
        {},  # Completely empty
        {"total_amount": None, "events": None},
        {"total_amount": "invalid_string", "events": [{"execution_duration_ms": "not_a_number"}]},
        {"events": [{"timestamp": "malformed_ts"}]},
    ]

    for c in malformed_cases:
        feat = FeatureExtractor.extract_features(c)
        assert isinstance(feat, dict)
        assert len(feat) == len(FEATURE_COLUMNS)
        for k, v in feat.items():
            assert isinstance(v, (int, float))
            assert not np.isnan(v)
            assert not np.isinf(v)


def test_bot_speed_flag_detection():
    """Verify that inhumanly fast execution activates the speed_anomaly_flag."""
    bot_case = {
        "total_amount": 50.0,
        "events": [
            {"event_name": "INITIATE_PAYMENT", "execution_duration_ms": 10},
            {"event_name": "VERIFY_PAYMENT", "execution_duration_ms": 15},
            {"event_name": "PAYMENT_SUCCESS", "execution_duration_ms": 12},
        ],
    }
    feat = FeatureExtractor.extract_features(bot_case)
    assert feat["mean_step_duration_ms"] < 50.0
    assert feat["speed_anomaly_flag"] == 1.0
