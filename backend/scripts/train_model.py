"""Model Training & Evaluation Script for WorkflowGuard Isolation Forest.

Trains an unsupervised Isolation Forest on normal baseline payment executions,
tunes the anomaly score threshold on a validation partition, and performs a
rigorous held-out evaluation with confusion matrix, false-positive rate, and
category breakdown.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to sys.path so 'app.*' imports work
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import numpy as np
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from app.engine.feature_extractor import FeatureExtractor
from app.engine.ml_engine import MLEngine
from scripts.generate_dataset import generate_synthetic_dataset


def run_training_pipeline(
    dataset_path: Optional[Path] = None,
    model_save_path: Optional[Path] = None,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Execute complete end-to-end dataset loading, training, calibration, and test evaluation."""
    print("=" * 75)
    print(" WorkflowGuard Isolation Forest Training Pipeline (Phase 3)")
    print("=" * 75)

    data_dir = BACKEND_ROOT / "data"
    models_dir = data_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    if dataset_path is None:
        dataset_path = data_dir / "synthetic_payment_dataset.json"

    if model_save_path is None:
        model_save_path = models_dir / "isolation_forest.joblib"

    metadata_path = models_dir / "model_metadata.json"

    # 1. Load or Generate Dataset
    if not dataset_path.exists():
        print(f"\n[1] Dataset not found at {dataset_path}. Generating 6,000 synthetic cases...")
        cases = generate_synthetic_dataset(n_cases=6000, output_path=dataset_path, seed=random_state)
    else:
        print(f"\n[1] Loading dataset from: {dataset_path}")
        with open(dataset_path, "r", encoding="utf-8") as f:
            cases = json.load(f)

    total_cases = len(cases)
    normal_cases = [c for c in cases if not c["is_anomaly"]]
    anomalous_cases = [c for c in cases if c["is_anomaly"]]

    print(f"    - Total Cases       : {total_cases}")
    print(f"    - Normal Executions : {len(normal_cases)} ({len(normal_cases)/total_cases*100:.1f}%)")
    print(f"    - Anomalous Cases   : {len(anomalous_cases)} ({len(anomalous_cases)/total_cases*100:.1f}%)")

    # 2. Case-Level Train / Validation / Test Splitting (70% / 15% / 15%)
    # We stratify by 'is_anomaly' to maintain consistent class proportions across partitions
    y_all = [1 if c["is_anomaly"] else 0 for c in cases]
    train_cases, temp_cases, _, y_temp = train_test_split(
        cases, y_all, test_size=0.30, random_state=random_state, stratify=y_all
    )
    val_cases, test_cases = train_test_split(
        temp_cases, test_size=0.50, random_state=random_state, stratify=y_temp
    )

    print(f"\n[2] Partitioning (Case-Level, Zero Leakage):")
    print(f"    - Training Set   : {len(train_cases)} cases")
    print(f"    - Validation Set : {len(val_cases)} cases")
    print(f"    - Test Set       : {len(test_cases)} cases")

    # 3. Feature Extraction
    print(f"\n[3] Extracting features for all partitions...")
    # Training is performed ONLY on normal cases within the training partition
    normal_train_cases = [c for c in train_cases if not c["is_anomaly"]]
    print(f"    - Normal training cases used for fitting: {len(normal_train_cases)}")

    X_train_df = FeatureExtractor.extract_batch(normal_train_cases)
    X_val_df = FeatureExtractor.extract_batch(val_cases)
    y_val = np.array([1 if c["is_anomaly"] else 0 for c in val_cases])

    X_test_df = FeatureExtractor.extract_batch(test_cases)
    y_test = np.array([1 if c["is_anomaly"] else 0 for c in test_cases])

    print(f"    - Feature count  : {X_train_df.shape[1]} columns")
    print(f"    - Columns        : {', '.join(X_train_df.columns)}")

    # 4. Model Training
    print(f"\n[4] Fitting Isolation Forest on normal baseline...")
    ml_engine = MLEngine(
        contamination=0.05,
        n_estimators=150,
        random_state=random_state,
    )
    ml_engine.fit(X_train_df)
    print("    -> Model fitting complete.")

    # 5. Threshold Calibration on Validation Set
    print(f"\n[5] Calibrating anomaly score threshold on Validation Set...")
    val_scores = ml_engine.compute_anomaly_score(X_val_df)

    best_thresh = 0.58
    best_f1 = 0.0
    candidate_thresholds = np.linspace(0.45, 0.75, 61)

    for cand in candidate_thresholds:
        preds = (val_scores >= cand).astype(int)
        f1 = f1_score(y_val, preds, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = float(cand)

    ml_engine.threshold = round(best_thresh, 4)
    print(f"    -> Optimal Threshold Selected: {ml_engine.threshold:.4f} (Val F1: {best_f1:.4f})")

    # 6. Evaluation on Held-Out Test Set (Frozen Model & Threshold)
    print(f"\n[6] Evaluating on Held-Out Test Set (N = {len(test_cases)})...")
    test_scores = ml_engine.compute_anomaly_score(X_test_df)
    test_preds = (test_scores >= ml_engine.threshold).astype(int)

    prec = float(precision_score(y_test, test_preds, zero_division=0))
    rec = float(recall_score(y_test, test_preds, zero_division=0))
    f1 = float(f1_score(y_test, test_preds, zero_division=0))
    cm = confusion_matrix(y_test, test_preds)
    tn, fp, fn, tp = cm.ravel()
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    print("\n" + "-" * 75)
    print(" OVERALL TEST SET PERFORMANCE:")
    print("-" * 75)
    print(f"  Precision          : {prec * 100:.2f}%")
    print(f"  Recall             : {rec * 100:.2f}%")
    print(f"  F1-Score           : {f1 * 100:.2f}%")
    print(f"  False Positive Rate: {fpr * 100:.2f}%")
    print(f"\n  Confusion Matrix:")
    print(f"    True Negatives (Normal detected Normal) : {tn}")
    print(f"    False Positives (Normal flagged Anomaly): {fp}")
    print(f"    False Negatives (Anomaly missed)        : {fn}")
    print(f"    True Positives (Anomaly detected)       : {tp}")

    # 7. Breakdown by Anomaly Category on Test Set
    print("\n" + "-" * 75)
    print(" PERFORMANCE BY CATEGORY ON TEST SET:")
    print("-" * 75)
    test_categories = [c["anomaly_category"] for c in test_cases]
    unique_cats = sorted(set(test_categories))

    cat_breakdown: Dict[str, Dict[str, Any]] = {}
    for cat in unique_cats:
        indices = [i for i, c in enumerate(test_categories) if c == cat]
        cat_actuals = y_test[indices]
        cat_preds = test_preds[indices]
        cat_scores = test_scores[indices]

        n_samples = len(indices)
        detected = int(np.sum(cat_preds))
        avg_score = float(np.mean(cat_scores))

        if cat in ("NORMAL_STANDARD", "NORMAL_RETRY", "RARE_LEGITIMATE"):
            fp_count = detected
            rate_label = f"False Positive Count: {fp_count}/{n_samples} ({fp_count/n_samples*100:.1f}%)"
        else:
            tp_count = detected
            rate_label = f"Detection Recall: {tp_count}/{n_samples} ({tp_count/n_samples*100:.1f}%)"

        print(f"  [{cat:<18}] N={n_samples:>3} | Mean Score: {avg_score:.4f} | {rate_label}")
        cat_breakdown[cat] = {
            "count": n_samples,
            "mean_score": round(avg_score, 4),
            "flagged_count": detected,
        }

    # 8. Rule-Valid Behavioral Outliers vs. Rule Violations Analysis
    rule_valid_anom_indices = [
        i for i, c in enumerate(test_categories)
        if c in ("BOT_SPEED", "AMOUNT_OUTLIER", "STALLED_WORKFLOW", "RAPID_RETRY_SPIKE")
    ]
    rule_viol_indices = [
        i for i, c in enumerate(test_categories) if c == "RULE_VIOLATION"
    ]

    rule_valid_recall = (
        float(np.mean(test_preds[rule_valid_anom_indices])) if rule_valid_anom_indices else 0.0
    )
    rule_viol_recall = (
        float(np.mean(test_preds[rule_viol_indices])) if rule_viol_indices else 0.0
    )

    print("\n" + "-" * 75)
    print(" SUBSYSTEM ANALYSIS (BEHAVIORAL vs. STRUCTURAL):")
    print("-" * 75)
    print(f"  Rule-Valid Behavioral Outliers Recall: {rule_valid_recall * 100:.2f}% (N = {len(rule_valid_anom_indices)})")
    print(f"  Syntactic Rule Violations Recall     : {rule_viol_recall * 100:.2f}% (N = {len(rule_viol_indices)})")
    print("  * Note: Rule violations are principally caught with 100% precision by the Phase 2 DFA;")
    print("    their detection here demonstrates ML feature sensitivity to transition anomalies.")

    # 9. Model and Metadata Persistence
    saved_model_file = ml_engine.save(model_save_path)
    print(f"\n[9] Saved trained model to: {saved_model_file}")

    metadata = {
        "model_type": "IsolationForest",
        "saved_model_file": str(saved_model_file),
        "trained_at": ml_engine.trained_at,
        "train_samples": ml_engine.train_sample_count,
        "n_estimators": ml_engine.n_estimators,
        "contamination": ml_engine.contamination,
        "calibrated_threshold": ml_engine.threshold,
        "feature_columns": list(X_train_df.columns),
        "test_metrics": {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "false_positive_rate": round(fpr, 4),
            "confusion_matrix": {
                "true_negatives": int(tn),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_positives": int(tp),
            },
            "category_breakdown": cat_breakdown,
            "rule_valid_behavioral_recall": round(rule_valid_recall, 4),
            "rule_violation_recall": round(rule_viol_recall, 4),
        },
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"    Saved metadata to: {metadata_path}")

    print("\n" + "=" * 75)
    print(" Isolation Forest training, calibration, and evaluation complete!")
    print("=" * 75)
    return metadata


if __name__ == "__main__":
    run_training_pipeline()
