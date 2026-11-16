"""Feature Extractor for WorkflowGuard Machine Learning Engine.

Transforms process execution traces and telemetry into fixed-dimension
numerical vectors suitable for Isolation Forest training and inference.
Guarantees consistent feature ordering, missing-value imputation, and strict
exclusion of identifiers and target labels.
"""

from datetime import datetime
from typing import Any, Dict, List, Sequence, Union

import numpy as np
import pandas as pd

# Canonical feature column names in strictly enforced order (20 features)
FEATURE_COLUMNS: Sequence[str] = (
    "amount",
    "log_amount",
    "amount_per_step",
    "total_duration_ms",
    "event_count",
    "mean_step_duration_ms",
    "max_step_duration_ms",
    "min_step_duration_ms",
    "mean_inter_event_delay_ms",
    "max_inter_event_delay_ms",
    "min_inter_event_delay_ms",
    "duration_per_event_ratio",
    "retry_count",
    "failure_count",
    "speed_anomaly_flag",
    "verifying_duration_ms",
    "initiating_duration_ms",
    "freq_initiate_payment",
    "freq_verify_payment",
    "freq_retry_payment",
)


class FeatureExtractor:
    """Extracts numerical features from execution traces."""

    feature_names: Sequence[str] = FEATURE_COLUMNS

    @classmethod
    def extract_features(cls, case_data: Union[Dict[str, Any], Any]) -> Dict[str, float]:
        """Convert a single case (dict or ORM ProcessCase) into a named feature dict."""
        # Normalize input attributes whether from dict or ORM model
        if isinstance(case_data, dict):
            raw_amount = case_data.get("total_amount")
            raw_duration = case_data.get("total_duration_ms")
            raw_retry = case_data.get("retry_count", 0)
            raw_failure = case_data.get("failure_count", 0)
            events = case_data.get("events") or []
            started_at = case_data.get("started_at")
            completed_at = case_data.get("completed_at")
        else:
            # SQLAlchemy ORM ProcessCase
            raw_amount = getattr(case_data, "total_amount", 0.0)
            raw_duration = None
            raw_retry = getattr(case_data, "retry_count", 0)
            raw_failure = 0
            events = getattr(case_data, "events", None) or []
            started_at = getattr(case_data, "started_at", None)
            completed_at = getattr(case_data, "completed_at", None)

        if not isinstance(events, (list, tuple)):
            events = []

        # 1. Parse amount safely
        amount = 0.0
        if raw_amount is not None:
            try:
                amount = max(0.0, float(raw_amount))
            except (ValueError, TypeError):
                amount = 0.0

        log_amount = float(np.log1p(amount))

        # 2. Extract event-level metrics
        event_count = len(events)
        amount_per_step = amount / max(1.0, float(event_count))

        step_durations: List[float] = []
        inter_delays: List[float] = []
        freq_initiate = 0
        freq_verify = 0
        freq_retry = 0
        verifying_duration = 0.0
        initiating_duration = 0.0
        failure_count = raw_failure

        prev_timestamp: Any = None

        for idx, ev in enumerate(events):
            # Normalize event properties
            if isinstance(ev, dict):
                ev_name = ev.get("event_name", "")
                from_s = ev.get("from_state", "")
                dur = ev.get("execution_duration_ms", 0)
                delay = ev.get("inter_event_delay_ms")
                ts = ev.get("timestamp")
            else:
                ev_name = getattr(ev, "event_name", "")
                from_s = getattr(ev, "from_state_key", "")
                dur = getattr(ev, "execution_duration_ms", 0)
                delay = None
                ts = getattr(ev, "timestamp", None)

            # Step duration
            try:
                dur_val = max(0.0, float(dur or 0))
            except (ValueError, TypeError):
                dur_val = 0.0
            step_durations.append(dur_val)

            # Inter-event delay
            if delay is not None:
                try:
                    delay_val = max(0.0, float(delay))
                except (ValueError, TypeError):
                    delay_val = 0.0
            elif ts is not None and prev_timestamp is not None:
                delay_val = cls._calculate_time_diff_ms(prev_timestamp, ts)
            else:
                delay_val = 0.0

            if idx > 0:
                inter_delays.append(delay_val)
            prev_timestamp = ts

            # Event frequencies
            if ev_name == "INITIATE_PAYMENT":
                freq_initiate += 1
            elif ev_name == "VERIFY_PAYMENT":
                freq_verify += 1
            elif ev_name == "RETRY_PAYMENT":
                freq_retry += 1
            elif ev_name == "PAYMENT_FAILURE":
                failure_count += 1

            # Stage dwell times
            if from_s in ("PAYMENT_VERIFYING",) or ev_name in ("VERIFY_PAYMENT",):
                verifying_duration += dur_val + delay_val
            elif from_s in ("PAYMENT_INITIATED",) or ev_name in ("INITIATE_PAYMENT",):
                initiating_duration += dur_val + delay_val

        # 3. Aggregations & Fallbacks
        if step_durations:
            mean_step_dur = float(np.mean(step_durations))
            max_step_dur = float(np.max(step_durations))
            min_step_dur = float(np.min(step_durations))
        else:
            mean_step_dur = 0.0
            max_step_dur = 0.0
            min_step_dur = 0.0

        if inter_delays:
            mean_delay = float(np.mean(inter_delays))
            max_delay = float(np.max(inter_delays))
            min_delay = float(np.min(inter_delays))
        else:
            mean_delay = 0.0
            max_delay = 0.0
            min_delay = 0.0

        # Total duration
        if raw_duration is not None:
            try:
                total_duration = max(0.0, float(raw_duration))
            except (ValueError, TypeError):
                total_duration = sum(step_durations) + sum(inter_delays)
        elif started_at and completed_at:
            total_duration = cls._calculate_time_diff_ms(started_at, completed_at)
        else:
            total_duration = sum(step_durations) + sum(inter_delays)

        ratio = total_duration / max(1.0, float(event_count))
        speed_flag = 1.0 if (event_count > 0 and mean_step_dur < 50.0) else 0.0

        return {
            "amount": amount,
            "log_amount": log_amount,
            "amount_per_step": amount_per_step,
            "total_duration_ms": total_duration,
            "event_count": float(event_count),
            "mean_step_duration_ms": mean_step_dur,
            "max_step_duration_ms": max_step_dur,
            "min_step_duration_ms": min_step_dur,
            "mean_inter_event_delay_ms": mean_delay,
            "max_inter_event_delay_ms": max_delay,
            "min_inter_event_delay_ms": min_delay,
            "duration_per_event_ratio": ratio,
            "retry_count": float(raw_retry),
            "failure_count": float(failure_count),
            "speed_anomaly_flag": speed_flag,
            "verifying_duration_ms": verifying_duration,
            "initiating_duration_ms": initiating_duration,
            "freq_initiate_payment": float(freq_initiate),
            "freq_verify_payment": float(freq_verify),
            "freq_retry_payment": float(freq_retry),
        }

    @classmethod
    def extract_vector(cls, case_data: Union[Dict[str, Any], Any]) -> np.ndarray:
        """Extract features as a 1D NumPy array adhering to FEATURE_COLUMNS order."""
        features = cls.extract_features(case_data)
        return np.array([features[col] for col in FEATURE_COLUMNS], dtype=np.float64)

    @classmethod
    def extract_batch(cls, cases: Sequence[Union[Dict[str, Any], Any]]) -> pd.DataFrame:
        """Extract a batch of cases into a Pandas DataFrame."""
        rows = [cls.extract_features(c) for c in cases]
        df = pd.DataFrame(rows, columns=list(FEATURE_COLUMNS))
        return df.fillna(0.0)

    @staticmethod
    def _calculate_time_diff_ms(t_start: Any, t_end: Any) -> float:
        """Safely calculate time difference in milliseconds between two timestamps."""
        try:
            if isinstance(t_start, str):
                t_start = datetime.fromisoformat(t_start.replace("Z", "+00:00"))
            if isinstance(t_end, str):
                t_end = datetime.fromisoformat(t_end.replace("Z", "+00:00"))
            delta = (t_end - t_start).total_seconds() * 1000.0
            return max(0.0, float(delta))
        except Exception:
            return 0.0
