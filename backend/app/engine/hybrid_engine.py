"""Hybrid Decision Engine for WorkflowGuard.

Arbitrates between the Deterministic Finite Automaton (DFA) syntactic engine
and the Isolation Forest statistical machine learning engine to produce
an explainable multi-tier anomaly verdict.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from app.engine.dfa_engine import (
    DFAEngine,
    DFAErrorType,
    TraceValidationResult,
    get_online_payment_dfa,
)
from app.engine.feature_extractor import FeatureExtractor
from app.engine.ml_engine import MLEngine, MLPredictionResult, ModelNotTrainedError
from app.models.anomaly import AnomalySeverityEnum, DetectorTypeEnum


class HybridClassification(str, Enum):
    """The four canonical hybrid decision verdicts."""

    NORMAL = "NORMAL"
    SYNTACTIC_ANOMALY = "SYNTACTIC_ANOMALY"
    BEHAVIORAL_ANOMALY = "BEHAVIORAL_ANOMALY"
    COMPOUND_ANOMALY = "COMPOUND_ANOMALY"


@dataclass
class HybridEvaluationResult:
    """Comprehensive verdict returned by the Hybrid Decision Engine."""

    # Hybrid verdict
    classification: HybridClassification
    is_anomaly: bool
    severity: AnomalySeverityEnum
    explanation: str

    # Execution status
    is_completed: bool
    is_partial: bool
    final_state: str
    visited_states: List[str]

    # DFA details
    dfa_is_valid: bool
    dfa_error_type: Optional[DFAErrorType] = None
    dfa_invalid_event: Optional[str] = None
    dfa_invalid_index: Optional[int] = None
    dfa_state_before_violation: Optional[str] = None
    dfa_message: Optional[str] = None

    # ML details
    ml_is_anomaly: bool = False
    ml_score: float = 0.0
    ml_threshold: float = 0.535
    top_contributing_features: List[Tuple[str, float]] = field(default_factory=list)
    feature_vector: Dict[str, float] = field(default_factory=dict)

    # Telemetry & Metadata
    workflow_code: str = "ONLINE_PAYMENT"
    model_version: str = "IsolationForest-v1"

    def to_dict(self) -> Dict[str, Any]:
        """Convert evaluation result into a JSON-serializable dictionary."""
        return {
            "classification": self.classification.value,
            "is_anomaly": self.is_anomaly,
            "severity": self.severity.value,
            "explanation": self.explanation,
            "is_completed": self.is_completed,
            "is_partial": self.is_partial,
            "final_state": self.final_state,
            "visited_states": self.visited_states,
            "dfa": {
                "is_valid": self.dfa_is_valid,
                "error_type": self.dfa_error_type.value if self.dfa_error_type else None,
                "invalid_event": self.dfa_invalid_event,
                "invalid_index": self.dfa_invalid_index,
                "state_before_violation": self.dfa_state_before_violation,
                "message": self.dfa_message,
            },
            "ml": {
                "is_anomaly": self.ml_is_anomaly,
                "score": round(self.ml_score, 4),
                "threshold": round(self.ml_threshold, 4),
                "top_contributing_features": self.top_contributing_features,
            },
            "metadata": {
                "workflow_code": self.workflow_code,
                "model_version": self.model_version,
            },
        }


class HybridEngine:
    """Arbitration engine combining DFA grammatical rules with ML outlier detection.

    Arbitration Matrix:
    1. DFA Valid & ML Normal   -> NORMAL (Severity: LOW)
    2. DFA Valid & ML Outlier  -> BEHAVIORAL_ANOMALY (Severity: MEDIUM or HIGH)
    3. DFA Invalid & ML Normal -> SYNTACTIC_ANOMALY (Severity: HIGH)
    4. DFA Invalid & ML Outlier-> COMPOUND_ANOMALY (Severity: CRITICAL)

    Invariants:
    - An invalid DFA transition CANNOT be overridden by a normal ML score.
    - Incomplete traces that adhere to DFA rules are marked as is_partial=True
      and are NOT classified as anomalies unless their continuous telemetry
      (amount, delays) is statistically abnormal.
    """

    def __init__(
        self,
        dfa_engine: Optional[DFAEngine] = None,
        ml_engine: Optional[MLEngine] = None,
    ):
        self.dfa_engine = dfa_engine or get_online_payment_dfa()
        self.ml_engine = ml_engine

    @classmethod
    def default(cls) -> "HybridEngine":
        """Instantiate HybridEngine with standard Online Payment DFA and loaded ML weights."""
        dfa = get_online_payment_dfa()
        try:
            ml = MLEngine.load()
        except (FileNotFoundError, ModelNotTrainedError):
            ml = None
        return cls(dfa_engine=dfa, ml_engine=ml)

    def evaluate_case(
        self,
        case_data: Union[Dict[str, Any], Any],
        custom_threshold: Optional[float] = None,
    ) -> HybridEvaluationResult:
        """Evaluate an entire case trace through both the DFA and ML engines."""
        # 1. Normalize events list for DFA validation
        if isinstance(case_data, dict):
            raw_events = case_data.get("events", [])
            initial_retries = case_data.get("retry_count", 0)
        else:
            raw_events = getattr(case_data, "events", [])
            initial_retries = getattr(case_data, "retry_count", 0)

        event_names: List[str] = []
        for ev in raw_events:
            if isinstance(ev, dict):
                event_names.append(ev.get("event_name", ""))
            else:
                event_names.append(getattr(ev, "event_name", ""))

        # 2. Evaluate DFA (Syntactic Layer)
        dfa_res: TraceValidationResult = self.dfa_engine.validate_trace(
            event_names, initial_retry_count=0
        )

        # 3. Evaluate ML (Behavioral Layer)
        features = FeatureExtractor.extract_features(case_data)
        ml_res: Optional[MLPredictionResult] = None
        ml_score = 0.0
        ml_is_anomaly = False
        top_features: List[Tuple[str, float]] = []
        threshold = 0.535

        if self.ml_engine and self.ml_engine.is_trained:
            thresh = custom_threshold or self.ml_engine.threshold
            ml_res = self.ml_engine.predict_case(case_data, custom_threshold=thresh)
            ml_score = ml_res.anomaly_score
            ml_is_anomaly = ml_res.is_anomaly
            top_features = ml_res.top_contributing_features
            threshold = ml_res.threshold

            # For in-progress (partial) executions, do not classify as anomalous
            # simply due to low event counts or absent future transitions.
            if dfa_res.is_partial and ml_is_anomaly:
                observed_anomaly = False
                for feat_name, z in top_features:
                    if feat_name in ("amount", "log_amount", "amount_per_step") and z > 3.0:
                        observed_anomaly = True
                        break
                    if feat_name in ("speed_anomaly_flag", "min_step_duration_ms", "mean_step_duration_ms") and features.get("speed_anomaly_flag", 0) == 1.0:
                        observed_anomaly = True
                        break
                    if feat_name in ("max_step_duration_ms", "total_duration_ms") and features.get("max_step_duration_ms", 0) > 300000.0:
                        observed_anomaly = True
                        break
                if not observed_anomaly and ml_score < 0.65:
                    ml_is_anomaly = False
        elif custom_threshold is not None:
            threshold = custom_threshold

        # 4. Decision Policy Arbitration
        dfa_valid = dfa_res.is_valid

        if dfa_valid and not ml_is_anomaly:
            classification = HybridClassification.NORMAL
            is_anomaly = False
            severity = AnomalySeverityEnum.LOW
            if dfa_res.is_completed:
                explanation = "Workflow trace executed successfully and conforms to both DFA rules and normal telemetry baseline."
            else:
                explanation = (
                    f"Workflow trace is valid and currently in-progress at state '{dfa_res.final_state}'. "
                    f"Telemetry remains within expected bounds."
                )

        elif dfa_valid and ml_is_anomaly:
            classification = HybridClassification.BEHAVIORAL_ANOMALY
            is_anomaly = True
            # Higher severity if score is very high (>= 0.65)
            severity = AnomalySeverityEnum.HIGH if ml_score >= 0.65 else AnomalySeverityEnum.MEDIUM
            top_str = ", ".join([f"{name} (+{z:.1f}σ)" for name, z in top_features[:3]])
            explanation = (
                f"Syntactically valid path, but statistical outlier detected by Isolation Forest. "
                f"Score: {ml_score:.4f} (Threshold: {threshold:.4f}). "
                f"Significant telemetry deviations: {top_str}."
            )

        elif not dfa_valid and not ml_is_anomaly:
            classification = HybridClassification.SYNTACTIC_ANOMALY
            is_anomaly = True
            severity = AnomalySeverityEnum.HIGH
            explanation = (
                f"Deterministic DFA grammar violation detected at step {dfa_res.first_invalid_index}: "
                f"Event '{dfa_res.first_invalid_event}' is invalid from state '{dfa_res.first_invalid_state}'. "
                f"Reason: {dfa_res.error_message}."
            )

        else:  # not dfa_valid and ml_is_anomaly
            classification = HybridClassification.COMPOUND_ANOMALY
            is_anomaly = True
            severity = AnomalySeverityEnum.CRITICAL
            top_str = ", ".join([f"{name} (+{z:.1f}σ)" for name, z in top_features[:3]])
            explanation = (
                f"Compound anomaly detected! Grammatical violation at step {dfa_res.first_invalid_index} "
                f"('{dfa_res.first_invalid_event}' from '{dfa_res.first_invalid_state}') "
                f"accompanied by behavioral telemetry outlier (Score: {ml_score:.4f}, Top factors: {top_str})."
            )

        return HybridEvaluationResult(
            classification=classification,
            is_anomaly=is_anomaly,
            severity=severity,
            explanation=explanation,
            is_completed=dfa_res.is_completed,
            is_partial=dfa_res.is_partial,
            final_state=dfa_res.final_state,
            visited_states=dfa_res.visited_states,
            dfa_is_valid=dfa_valid,
            dfa_error_type=dfa_res.error_type,
            dfa_invalid_event=dfa_res.first_invalid_event,
            dfa_invalid_index=dfa_res.first_invalid_index,
            dfa_state_before_violation=dfa_res.first_invalid_state,
            dfa_message=dfa_res.error_message,
            ml_is_anomaly=ml_is_anomaly,
            ml_score=ml_score,
            ml_threshold=threshold,
            top_contributing_features=top_features,
            feature_vector=features,
            workflow_code=self.dfa_engine.workflow_code,
            model_version="IsolationForest-v1" if self.ml_engine else "Unavailable",
        )
