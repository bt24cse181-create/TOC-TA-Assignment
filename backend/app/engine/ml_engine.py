"""Machine Learning Anomaly Detection Engine using Isolation Forest.

Provides unsupervised behavioral anomaly detection over process telemetry,
independent of DFA syntactic rules.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.engine.feature_extractor import FEATURE_COLUMNS, FeatureExtractor


class ModelNotTrainedError(Exception):
    """Raised when prediction is requested on an uninitialized or unpersisted model."""

    pass


@dataclass
class MLPredictionResult:
    """Detection result for a single process execution trace."""

    is_anomaly: bool
    anomaly_score: float  # [0.0, 1.0], higher = more anomalous
    threshold: float
    feature_vector: Dict[str, float]
    top_contributing_features: List[Tuple[str, float]] = field(default_factory=list)

    def summary(self) -> str:
        status = "ANOMALY" if self.is_anomaly else "NORMAL"
        top_str = ", ".join([f"{k} (+{v:.1f}σ)" for k, v in self.top_contributing_features[:3]])
        return f"{status} [Score: {self.anomaly_score:.3f} | Thresh: {self.threshold:.3f}] - Key Factors: {top_str}"


class MLEngine:
    """Isolation Forest Anomaly Detection Engine for Workflow Telemetry.

    Anomaly Score Formulation:
        scikit-learn's IsolationForest outputs score_samples(X) such that:
        - Normal instances receive values near -0.35 to -0.45.
        - Anomalies receive lower values (< -0.55).

        This engine transforms raw scores into an intuitive, normalized score:
            s(x) = clip(-score_samples(x), 0.0, 1.0)
        Where:
            0.0 <= s(x) < 0.50 : High confidence normal
            0.50 <= s(x) < T   : Borderline normal
            s(x) >= T          : Anomalous behavioral outlier (default T ~ 0.58)
    """

    DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "models"
    DEFAULT_MODEL_PATH = DEFAULT_MODEL_DIR / "isolation_forest.joblib"

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 150,
        random_state: int = 42,
        threshold: float = 0.58,
    ):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.threshold = threshold

        self.model: Optional[IsolationForest] = None
        self.feature_names: List[str] = list(FEATURE_COLUMNS)
        self.feature_means: Dict[str, float] = {}
        self.feature_stds: Dict[str, float] = {}
        self.trained_at: Optional[str] = None
        self.train_sample_count: int = 0

    @property
    def is_trained(self) -> bool:
        """Return True if model weights are loaded and ready for inference."""
        return self.model is not None

    def fit(
        self,
        X_train: Union[pd.DataFrame, np.ndarray],
        feature_names: Optional[Sequence[str]] = None,
    ) -> "MLEngine":
        """Train Isolation Forest on normal baseline executions."""
        if isinstance(X_train, pd.DataFrame):
            self.feature_names = list(X_train.columns)
            X_mat = X_train.values
        else:
            self.feature_names = list(feature_names or FEATURE_COLUMNS)
            X_mat = np.asarray(X_train)

        # Compute baseline mean and std for feature attribution
        self.feature_means = {
            name: float(np.mean(X_mat[:, i])) for i, name in enumerate(self.feature_names)
        }
        self.feature_stds = {
            name: max(1e-6, float(np.std(X_mat[:, i]))) for i, name in enumerate(self.feature_names)
        }

        # Initialize and fit scikit-learn IsolationForest
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.model.fit(X_mat)

        self.train_sample_count = len(X_mat)
        self.trained_at = datetime.now(timezone.utc).isoformat()
        return self

    def compute_anomaly_score(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Compute continuous anomaly score s(x) in [0.0, 1.0]."""
        if not self.is_trained or self.model is None:
            raise ModelNotTrainedError(
                "Cannot compute anomaly scores: Isolation Forest model has not been trained."
            )

        X_mat = X.values if isinstance(X, pd.DataFrame) else np.asarray(X)
        if X_mat.ndim == 1:
            X_mat = X_mat.reshape(1, -1)

        # scikit-learn raw score_samples: more negative = more anomalous
        raw_scores = self.model.score_samples(X_mat)
        # Transform to positive scale where larger values = more anomalous
        scores = -raw_scores
        return np.clip(scores, 0.0, 1.0)

    def predict_case(
        self,
        case_data: Union[Dict[str, Any], Any],
        custom_threshold: Optional[float] = None,
    ) -> MLPredictionResult:
        """Extract features and predict anomaly status for a single case."""
        if not self.is_trained:
            raise ModelNotTrainedError(
                "MLEngine cannot predict: model is not trained. "
                "Run 'python backend/scripts/train_model.py' first or call mle.load()."
            )

        features = FeatureExtractor.extract_features(case_data)
        vec = np.array([features[col] for col in self.feature_names], dtype=np.float64)

        score = float(self.compute_anomaly_score(vec)[0])
        thresh = custom_threshold if custom_threshold is not None else self.threshold
        is_anomaly = bool(score >= thresh)

        # Calculate top contributing features based on standard deviations from baseline
        deviations: List[Tuple[str, float]] = []
        for name in self.feature_names:
            val = features.get(name, 0.0)
            mean = self.feature_means.get(name, 0.0)
            std = self.feature_stds.get(name, 1.0)
            z_score = abs(val - mean) / std
            if z_score > 1.5:  # Significant deviation threshold
                deviations.append((name, round(float(z_score), 2)))

        deviations.sort(key=lambda x: x[1], reverse=True)

        return MLPredictionResult(
            is_anomaly=is_anomaly,
            anomaly_score=round(score, 4),
            threshold=thresh,
            feature_vector=features,
            top_contributing_features=deviations[:5],
        )

    def save(self, filepath: Optional[Union[str, Path]] = None) -> Path:
        """Persist model bundle to disk via Joblib."""
        if not self.is_trained or self.model is None:
            raise ModelNotTrainedError("Cannot save an untrained MLEngine.")

        target = Path(filepath) if filepath else self.DEFAULT_MODEL_PATH
        target.parent.mkdir(parents=True, exist_ok=True)

        bundle = {
            "model": self.model,
            "feature_names": list(self.feature_names),
            "feature_means": self.feature_means,
            "feature_stds": self.feature_stds,
            "threshold": self.threshold,
            "contamination": self.contamination,
            "n_estimators": self.n_estimators,
            "random_state": self.random_state,
            "trained_at": self.trained_at,
            "train_sample_count": self.train_sample_count,
        }

        joblib.dump(bundle, target)
        return target

    @classmethod
    def load(cls, filepath: Optional[Union[str, Path]] = None) -> "MLEngine":
        """Load trained model bundle from disk."""
        target = Path(filepath) if filepath else cls.DEFAULT_MODEL_PATH
        if not target.exists():
            raise FileNotFoundError(
                f"Trained model file not found at: {target}. "
                f"Execute 'python backend/scripts/train_model.py' to train and save the model."
            )

        bundle = joblib.load(target)
        engine = cls(
            contamination=bundle.get("contamination", 0.05),
            n_estimators=bundle.get("n_estimators", 150),
            random_state=bundle.get("random_state", 42),
            threshold=bundle.get("threshold", 0.58),
        )
        engine.model = bundle["model"]
        engine.feature_names = bundle["feature_names"]
        engine.feature_means = bundle.get("feature_means", {})
        engine.feature_stds = bundle.get("feature_stds", {})
        engine.trained_at = bundle.get("trained_at")
        engine.train_sample_count = bundle.get("train_sample_count", 0)
        return engine
