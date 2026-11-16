"""WorkflowGuard Automata & Decision Engine Package."""

from app.engine.dfa_engine import (
    DFAEngine,
    DFAErrorType,
    DFAState,
    DFATransition,
    TraceValidationResult,
    TransitionResult,
    WorkflowDefinitionError,
    get_online_payment_dfa,
)
from app.engine.feature_extractor import (
    FEATURE_COLUMNS,
    FeatureExtractor,
)
from app.engine.hybrid_engine import (
    HybridClassification,
    HybridEngine,
    HybridEvaluationResult,
)
from app.engine.ml_engine import (
    MLEngine,
    MLPredictionResult,
    ModelNotTrainedError,
)

__all__ = [
    # DFA Engine (Phase 2)
    "DFAEngine",
    "DFAState",
    "DFATransition",
    "TransitionResult",
    "TraceValidationResult",
    "DFAErrorType",
    "WorkflowDefinitionError",
    "get_online_payment_dfa",
    # ML Engine (Phase 3)
    "FEATURE_COLUMNS",
    "FeatureExtractor",
    "MLEngine",
    "MLPredictionResult",
    "ModelNotTrainedError",
    # Hybrid Engine (Phase 4)
    "HybridClassification",
    "HybridEngine",
    "HybridEvaluationResult",
]
