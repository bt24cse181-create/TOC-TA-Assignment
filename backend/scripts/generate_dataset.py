"""Synthetic Payment Dataset Generator for WorkflowGuard ML Engine.

Generates realistic process execution traces with normal workflows,
statistically unusual behavioral anomalies (bot speeds, extreme amounts,
stalls, retry spikes), and rule-violating sequences.

ASSUMPTIONS & METHODOLOGY:
1. Normal e-commerce transactions have log-normal amount distributions ($10 - $500).
2. Human checkout timings have realistic step delays (500ms - 8000ms per step).
3. Bot attacks execute steps with sub-human latency (< 50ms).
4. Stalled workflows experience timeouts or multi-minute delays (> 15 minutes).
5. Ground-truth labels and categories are stored strictly for evaluation and
   must NEVER be supplied to the feature extractor or training algorithm.
"""

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


def generate_synthetic_dataset(
    n_cases: int = 6000,
    output_path: Optional[Path] = None,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Generate a reproducible dataset of synthetic payment execution cases."""
    random.seed(seed)
    np.random.seed(seed)

    cases: List[Dict[str, Any]] = []

    # Category distribution targets:
    # ~85% Normal / Benign:
    #   - Standard Happy Path (~70%)
    #   - Benign Single Retry (~10%)
    #   - Rare Legitimate (~5%) (high amount, slow connection, or 2 retries)
    # ~15% Anomalies:
    #   - Bot Speed (~4%)
    #   - Extreme Amount (~4%)
    #   - Stalled Workflow (~3%)
    #   - Rapid Retry Spike (~2%)
    #   - Rule Violations (~2%)

    n_normal_standard = int(n_cases * 0.70)
    n_normal_retry = int(n_cases * 0.10)
    n_rare_legit = int(n_cases * 0.05)
    n_bot_speed = int(n_cases * 0.04)
    n_extreme_amount = int(n_cases * 0.04)
    n_stalled = int(n_cases * 0.03)
    n_rapid_retry = int(n_cases * 0.02)
    n_rule_violation = n_cases - (
        n_normal_standard + n_normal_retry + n_rare_legit +
        n_bot_speed + n_extreme_amount + n_stalled + n_rapid_retry
    )

    configs = [
        ("NORMAL_STANDARD", n_normal_standard, False),
        ("NORMAL_RETRY", n_normal_retry, False),
        ("RARE_LEGITIMATE", n_rare_legit, False),
        ("BOT_SPEED", n_bot_speed, True),
        ("AMOUNT_OUTLIER", n_extreme_amount, True),
        ("STALLED_WORKFLOW", n_stalled, True),
        ("RAPID_RETRY_SPIKE", n_rapid_retry, True),
        ("RULE_VIOLATION", n_rule_violation, True),
    ]

    base_time = datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc)
    case_counter = 1

    for category, count, is_anomaly in configs:
        for _ in range(count):
            case_id = f"CASE-{case_counter:05d}"
            user_id = f"USR-{random.randint(1000, 9999)}"
            case_start = base_time + timedelta(
                days=random.randint(0, 20),
                seconds=random.randint(0, 86400),
            )

            case_data = _generate_single_case(
                case_id=case_id,
                user_id=user_id,
                start_time=case_start,
                category=category,
                is_anomaly=is_anomaly,
            )
            cases.append(case_data)
            case_counter += 1

    # Shuffle cases to avoid ordering bias during cross-validation
    random.shuffle(cases)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cases, f, indent=2)
        print(f"Generated {len(cases)} cases saved to {output_path}")

    return cases


def _generate_single_case(
    case_id: str,
    user_id: str,
    start_time: datetime,
    category: str,
    is_anomaly: bool,
) -> Dict[str, Any]:
    """Generate events and telemetry for a single execution case."""
    events: List[Dict[str, Any]] = []
    current_time = start_time
    retry_count = 0
    failure_count = 0

    # 1. Determine Amount ($)
    if category == "AMOUNT_OUTLIER":
        # Extreme outlier: $8,000 to $95,000
        amount = round(float(np.random.uniform(8000.0, 95000.0)), 2)
    elif category == "RARE_LEGITIMATE":
        # High but legitimate purchase: $800 to $2,500
        amount = round(float(np.random.uniform(800.0, 2500.0)), 2)
    else:
        # Standard e-commerce lognormal distribution (~$15 - $350)
        amount = round(float(np.random.lognormal(mean=4.1, sigma=0.85)), 2)
        amount = max(5.0, min(amount, 999.0))

    # Helper to add an event
    def add_event(name: str, from_s: str, to_s: str, duration_ms: int, delay_ms: int):
        nonlocal current_time
        current_time += timedelta(milliseconds=delay_ms + duration_ms)
        events.append({
            "event_name": name,
            "from_state": from_s,
            "to_state": to_s,
            "timestamp": current_time.isoformat(),
            "execution_duration_ms": duration_ms,
            "inter_event_delay_ms": delay_ms,
            "retry_count": retry_count,
        })

    # Step durations and delays by category:
    if category == "BOT_SPEED":
        # Inhumanly fast sub-millisecond to 40ms transitions
        def get_dur(): return random.randint(2, 25)
        def get_delay(): return random.randint(1, 15)
    elif category == "STALLED_WORKFLOW":
        # Multi-minute / hung process delays (10 - 60 minutes)
        def get_dur(): return random.randint(500, 3000)
        def get_delay(): return random.randint(600000, 3600000)
    elif category == "RAPID_RETRY_SPIKE":
        # Normal step durations, but immediate rapid retry delays (< 50ms)
        def get_dur(): return random.randint(200, 1000)
        def get_delay(): return random.randint(10, 50)
    else:
        # Normal human execution delays (500ms - 5000ms)
        def get_dur(): return int(np.random.normal(loc=1200, scale=350))
        def get_delay(): return int(np.random.exponential(scale=1800))

    # Clamp human values
    def safe_dur(): return max(50, get_dur()) if category != "BOT_SPEED" else get_dur()
    def safe_delay(): return max(20, get_delay()) if category not in ("BOT_SPEED", "RAPID_RETRY_SPIKE") else get_delay()

    # 2. Build Event Sequence according to scenario
    if category == "NORMAL_STANDARD":
        # CREATE -> INITIATE -> VERIFY -> SUCCESS -> CONFIRMED
        add_event("INITIATE_PAYMENT", "ORDER_CREATED", "PAYMENT_INITIATED", safe_dur(), safe_delay())
        add_event("VERIFY_PAYMENT", "PAYMENT_INITIATED", "PAYMENT_VERIFYING", safe_dur(), safe_delay())
        add_event("PAYMENT_SUCCESS", "PAYMENT_VERIFYING", "ORDER_CONFIRMED", safe_dur(), safe_delay())
        final_state = "ORDER_CONFIRMED"

    elif category == "NORMAL_RETRY":
        # Failed once, retried, confirmed
        add_event("INITIATE_PAYMENT", "ORDER_CREATED", "PAYMENT_INITIATED", safe_dur(), safe_delay())
        add_event("VERIFY_PAYMENT", "PAYMENT_INITIATED", "PAYMENT_VERIFYING", safe_dur(), safe_delay())
        add_event("PAYMENT_FAILURE", "PAYMENT_VERIFYING", "PAYMENT_FAILED", safe_dur(), safe_delay())
        failure_count += 1
        retry_count = 1
        add_event("RETRY_PAYMENT", "PAYMENT_FAILED", "PAYMENT_INITIATED", safe_dur(), safe_delay())
        add_event("VERIFY_PAYMENT", "PAYMENT_INITIATED", "PAYMENT_VERIFYING", safe_dur(), safe_delay())
        add_event("PAYMENT_SUCCESS", "PAYMENT_VERIFYING", "ORDER_CONFIRMED", safe_dur(), safe_delay())
        final_state = "ORDER_CONFIRMED"

    elif category == "RARE_LEGITIMATE":
        # Either 2 retries, or user cancellation after delay
        if random.random() < 0.6:
            # 2 retries, then success
            add_event("INITIATE_PAYMENT", "ORDER_CREATED", "PAYMENT_INITIATED", safe_dur(), safe_delay())
            add_event("VERIFY_PAYMENT", "PAYMENT_INITIATED", "PAYMENT_VERIFYING", safe_dur(), safe_delay())
            add_event("PAYMENT_FAILURE", "PAYMENT_VERIFYING", "PAYMENT_FAILED", safe_dur(), safe_delay())
            failure_count += 1
            retry_count = 1
            add_event("RETRY_PAYMENT", "PAYMENT_FAILED", "PAYMENT_INITIATED", safe_dur(), safe_delay())
            add_event("VERIFY_PAYMENT", "PAYMENT_INITIATED", "PAYMENT_VERIFYING", safe_dur(), safe_delay())
            add_event("PAYMENT_FAILURE", "PAYMENT_VERIFYING", "PAYMENT_FAILED", safe_dur(), safe_delay())
            failure_count += 1
            retry_count = 2
            add_event("RETRY_PAYMENT", "PAYMENT_FAILED", "PAYMENT_INITIATED", safe_dur(), safe_delay())
            add_event("VERIFY_PAYMENT", "PAYMENT_INITIATED", "PAYMENT_VERIFYING", safe_dur(), safe_delay())
            add_event("PAYMENT_SUCCESS", "PAYMENT_VERIFYING", "ORDER_CONFIRMED", safe_dur(), safe_delay())
            final_state = "ORDER_CONFIRMED"
        else:
            # Cancelled order after initiated
            add_event("INITIATE_PAYMENT", "ORDER_CREATED", "PAYMENT_INITIATED", safe_dur(), safe_delay())
            add_event("CANCEL_ORDER", "PAYMENT_INITIATED", "ORDER_CANCELLED", safe_dur(), safe_delay())
            final_state = "ORDER_CANCELLED"

    elif category in ("BOT_SPEED", "AMOUNT_OUTLIER", "STALLED_WORKFLOW"):
        # Rule-valid sequence, but anomalous behavioral dimensions
        add_event("INITIATE_PAYMENT", "ORDER_CREATED", "PAYMENT_INITIATED", safe_dur(), safe_delay())
        add_event("VERIFY_PAYMENT", "PAYMENT_INITIATED", "PAYMENT_VERIFYING", safe_dur(), safe_delay())
        add_event("PAYMENT_SUCCESS", "PAYMENT_VERIFYING", "ORDER_CONFIRMED", safe_dur(), safe_delay())
        final_state = "ORDER_CONFIRMED"

    elif category == "RAPID_RETRY_SPIKE":
        # Rapid fire retry loop
        add_event("INITIATE_PAYMENT", "ORDER_CREATED", "PAYMENT_INITIATED", safe_dur(), safe_delay())
        add_event("VERIFY_PAYMENT", "PAYMENT_INITIATED", "PAYMENT_VERIFYING", safe_dur(), safe_delay())
        add_event("PAYMENT_FAILURE", "PAYMENT_VERIFYING", "PAYMENT_FAILED", safe_dur(), safe_delay())
        failure_count += 1
        for r in range(1, 3):
            retry_count = r
            add_event("RETRY_PAYMENT", "PAYMENT_FAILED", "PAYMENT_INITIATED", safe_dur(), safe_delay())
            add_event("VERIFY_PAYMENT", "PAYMENT_INITIATED", "PAYMENT_VERIFYING", safe_dur(), safe_delay())
            add_event("PAYMENT_FAILURE", "PAYMENT_VERIFYING", "PAYMENT_FAILED", safe_dur(), safe_delay())
            failure_count += 1
        # Then cancelled
        add_event("CANCEL_ORDER", "PAYMENT_FAILED", "ORDER_CANCELLED", safe_dur(), safe_delay())
        final_state = "ORDER_CANCELLED"

    elif category == "RULE_VIOLATION":
        # Syntactic violations (e.g. skip verification or retry exhaustion)
        if random.random() < 0.5:
            # Skip verify directly to payment success
            add_event("INITIATE_PAYMENT", "ORDER_CREATED", "PAYMENT_INITIATED", safe_dur(), safe_delay())
            add_event("PAYMENT_SUCCESS", "PAYMENT_INITIATED", "TRAP_STATE", safe_dur(), safe_delay())
            final_state = "TRAP_STATE"
        else:
            # Direct confirm from created
            add_event("PAYMENT_SUCCESS", "ORDER_CREATED", "TRAP_STATE", safe_dur(), safe_delay())
            final_state = "TRAP_STATE"

    total_duration_ms = int((current_time - start_time).total_seconds() * 1000)

    return {
        "case_id": case_id,
        "user_id": user_id,
        "started_at": start_time.isoformat(),
        "completed_at": current_time.isoformat(),
        "total_duration_ms": total_duration_ms,
        "total_amount": amount,
        "final_state": final_state,
        "retry_count": retry_count,
        "failure_count": failure_count,
        "is_anomaly": is_anomaly,
        "anomaly_category": category,
        "events": events,
    }


if __name__ == "__main__":
    dataset_file = Path(__file__).resolve().parent.parent / "data" / "synthetic_payment_dataset.json"
    generate_synthetic_dataset(n_cases=6000, output_path=dataset_file, seed=42)
