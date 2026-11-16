"""Unit tests for MLEngine (Isolation Forest Anomaly Detection)."""

import json
from pathlib import Path

import numpy as np
import pytest

from app.engine.ml_engine import (
    MLEngine,
    MLPredictionResult,
    ModelNotTrainedError,
)
from scripts.generate_dataset import generate_synthetic_dataset


def test_untrained_model_raises_error():
    """Verify that calling prediction methods on an untrained model raises ModelNotTrainedError."""
    engine = MLEngine()
    assert engine.is_trained is False

    with pytest.raises(ModelNotTrainedError):
        engine.compute_anomaly_score(np.zeros((1, 20)))

    with pytest.raises(ModelNotTrainedError):
        engine.predict_case({"total_amount": 50.0, "events": []})


def test_model_training_and_scoring():
    """Verify model fitting on normal data and scoring consistency."""
    np.random.seed(42)
    # Generate 100 normal samples (clustered around 10.0)
    X_normal = np.random.normal(loc=10.0, scale=1.0, size=(100, 20))
    # Extreme outlier (all features at 5000.0)
    X_outlier = np.full((1, 20), 5000.0)

    engine = MLEngine(contamination=0.05, n_estimators=50, random_state=42)
    engine.fit(X_normal)

    assert engine.is_trained is True

    normal_scores = engine.compute_anomaly_score(X_normal[:5])
    outlier_score = engine.compute_anomaly_score(X_outlier)[0]

    # Scores must be in [0.0, 1.0]
    assert np.all((normal_scores >= 0.0) & (normal_scores <= 1.0))
    assert 0.0 <= outlier_score <= 1.0

    # Outlier score must be significantly higher than average normal score
    assert outlier_score > np.mean(normal_scores)


def test_predict_case_threshold_logic():
    """Verify that is_anomaly is determined strictly by score >= threshold."""
    engine = MLEngine(threshold=0.55)
    # Mocking trained state
    np.random.seed(42)
    engine.fit(np.random.normal(loc=10.0, scale=1.0, size=(50, 20)))

    case_normal = {"total_amount": 10.0, "events": []}
    case_extreme = {"total_amount": 999999.0, "events": [{"execution_duration_ms": 1}]}

    res_norm = engine.predict_case(case_normal)
    res_ext = engine.predict_case(case_extreme)

    assert isinstance(res_norm, MLPredictionResult)
    assert res_norm.is_anomaly == (res_norm.anomaly_score >= res_norm.threshold)
    assert res_ext.is_anomaly == (res_ext.anomaly_score >= res_ext.threshold)


def test_model_save_and_load_persistence(tmp_path: Path):
    """Verify model serialization and deserialization via Joblib preserves weights and outputs."""
    np.random.seed(42)
    X_train = np.random.normal(loc=50.0, scale=5.0, size=(80, 20))

    engine = MLEngine(threshold=0.57, n_estimators=40, random_state=42)
    engine.fit(X_train)

    save_file = tmp_path / "test_iso_forest.joblib"
    engine.save(save_file)
    assert save_file.exists()

    # Load into new instance
    loaded = MLEngine.load(save_file)
    assert loaded.is_trained is True
    assert loaded.threshold == 0.57
    assert loaded.feature_names == engine.feature_names

    # Check identical predictions
    test_sample = np.random.normal(loc=50.0, scale=5.0, size=(5, 20))
    orig_scores = engine.compute_anomaly_score(test_sample)
    loaded_scores = loaded.compute_anomaly_score(test_sample)

    np.testing.assert_allclose(orig_scores, loaded_scores, rtol=1e-5)


def test_feature_attribution_ranking():
    """Verify that top contributing features are identified and sorted by deviation."""
    engine = MLEngine(random_state=42)
    X_train = np.random.normal(loc=10.0, scale=1.0, size=(60, 20))
    engine.fit(X_train)

    # Construct case where amount is 500.0 (extreme) while others are ~10.0
    case = {
        "total_amount": 500.0,
        "events": [],
    }
    res = engine.predict_case(case)
    assert len(res.top_contributing_features) > 0
    top_feature_name, z_score = res.top_contributing_features[0]
    # 'amount' or 'log_amount' must be top feature
    assert top_feature_name in ("amount", "log_amount", "amount_per_step")
    assert z_score > 3.0


def test_synthetic_dataset_reproducibility():
    """Verify that generate_synthetic_dataset is strictly deterministic with fixed seed."""
    data1 = generate_synthetic_dataset(n_cases=50, seed=123)
    data2 = generate_synthetic_dataset(n_cases=50, seed=123)
    data3 = generate_synthetic_dataset(n_cases=50, seed=999)

    # Identical seed -> identical cases
    assert json.dumps(data1) == json.dumps(data2)
    # Different seed -> different cases
    assert json.dumps(data1) != json.dumps(data3)


def test_loaded_production_model_smoke():
    """Verify that the production trained model bundle can be loaded and executes inference."""
    try:
        model = MLEngine.load()
    except FileNotFoundError:
        pytest.skip("Default trained model file not present yet.")

    assert model.is_trained is True
    sample_case = {
        "total_amount": 99.0,
        "events": [
            {"event_name": "INITIATE_PAYMENT", "execution_duration_ms": 1200},
            {"event_name": "VERIFY_PAYMENT", "execution_duration_ms": 1300},
            {"event_name": "PAYMENT_SUCCESS", "execution_duration_ms": 800},
        ],
    }
    pred = model.predict_case(sample_case)
    assert isinstance(pred, MLPredictionResult)
    assert 0.0 <= pred.anomaly_score <= 1.0
