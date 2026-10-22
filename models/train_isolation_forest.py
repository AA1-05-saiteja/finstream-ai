"""
FinStream AI - Unsupervised Isolation Forest Anomaly Detection Training & Evaluation
Trains an Isolation Forest model without ground-truth labels and benchmarks against synthetic test labels.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# Ensure project root is in sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import settings
from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS
from models.training_data import generate_synthetic_dataset, get_train_test_split

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("train_isolation_forest")


def train_and_evaluate_isolation_forest(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[IsolationForest, Dict[str, Any]]:
    """
    Fits an unsupervised Isolation Forest model (NO labels during fit)
    and benchmarks predictions against synthetic ground-truth test labels.
    """
    default_params = {
        "n_estimators": 100,
        "contamination": 0.10,
        "max_samples": "auto",
        "random_state": 42,
        "n_jobs": -1,
    }
    if params:
        default_params.update(params)

    logger.info("Training Isolation Forest (Unsupervised) with parameters: %s", default_params)
    model = IsolationForest(**default_params)
    # Strictly fit on X_train WITHOUT y_train
    model.fit(X_train)

    # Scikit-Learn IsolationForest conventions:
    # 1. decision_function: large negative values = anomalous, positive values = normal
    #    Inverted score (-decision_function): higher = more anomalous (for ROC-AUC / PR-AUC)
    raw_decision = model.decision_function(X_test)
    anomaly_scores = -raw_decision

    # 2. predict: returns -1 for outlier/anomaly, +1 for inlier/normal
    raw_preds = model.predict(X_test)
    y_pred = np.where(raw_preds == -1, 1, 0)

    # Compute benchmarking metrics
    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, anomaly_scores))
    pr_auc = float(average_precision_score(y_test, anomaly_scores))
    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        "model_name": "IsolationForest",
        "parameters": {k: (str(v) if not isinstance(v, (int, float, bool, str)) else v) for k, v in default_params.items()},
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "test_anomalies": int(y_test.sum()),
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "confusion_matrix": {
            "tn": cm[0][0],
            "fp": cm[0][1],
            "fn": cm[1][0],
            "tp": cm[1][1],
        },
    }

    logger.info(
        "Isolation Forest Benchmark: Precision=%.4f, Recall=%.4f, F1=%.4f, ROC-AUC=%.4f, PR-AUC=%.4f",
        prec,
        rec,
        f1,
        roc_auc,
        pr_auc,
    )
    return model, metrics


def save_isolation_forest_artifacts(
    model: IsolationForest,
    metrics: Dict[str, Any],
    artifacts_dir: str = "models/artifacts",
) -> Dict[str, str]:
    """Saves serialized model and metrics to artifacts directory."""
    out_dir = Path(artifacts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    joblib_path = out_dir / "isolation_forest.joblib"
    metrics_path = out_dir / "isolation_forest_metrics.json"

    joblib.dump(model, joblib_path)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Isolation Forest artifacts saved to %s", out_dir)
    return {
        "joblib": str(joblib_path),
        "metrics": str(metrics_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FinStream AI Unsupervised Isolation Forest Training Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--samples", type=int, default=10000, help="Number of synthetic samples")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--contamination", type=float, default=0.10, help="Estimated outlier contamination ratio")
    parser.add_argument("--artifacts-dir", type=str, default="models/artifacts", help="Output directory for artifacts")
    return parser.parse_args()


def main():
    args = parse_args()
    df = generate_synthetic_dataset(num_samples=args.samples, random_seed=args.seed)
    X_train, X_test, _, y_test = get_train_test_split(df, random_state=args.seed)

    model, metrics = train_and_evaluate_isolation_forest(
        X_train,
        X_test,
        y_test,
        params={"contamination": args.contamination, "random_state": args.seed},
    )
    save_isolation_forest_artifacts(model, metrics, artifacts_dir=args.artifacts_dir)


if __name__ == "__main__":
    main()
