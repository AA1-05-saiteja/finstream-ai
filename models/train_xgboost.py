"""
FinStream AI - Supervised XGBoost Anomaly Classifier Training & Evaluation
Trains and benchmarks an XGBoost binary classifier on synthetic transaction features.
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
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier

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
logger = logging.getLogger("train_xgboost")


def train_and_evaluate_xgboost(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    params: Optional[Dict[str, Any]] = None,
    threshold: float = 0.50,
) -> Tuple[XGBClassifier, Dict[str, Any]]:
    """
    Trains an XGBoost classifier and evaluates performance on held-out test data.
    """
    default_params = {
        "n_estimators": 100,
        "max_depth": 5,
        "learning_rate": 0.08,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "eval_metric": "logloss",
        "n_jobs": -1,
    }
    if params:
        default_params.update(params)

    logger.info("Training XGBoost Classifier with parameters: %s", default_params)
    model = XGBClassifier(**default_params)
    model.fit(X_train, y_train)

    # Inference on test set
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)

    # Compute comprehensive evaluation metrics
    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_proba))
    pr_auc = float(average_precision_score(y_test, y_proba))
    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        "model_name": "XGBoost",
        "parameters": default_params,
        "classification_threshold": threshold,
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
        "XGBoost Evaluation: Precision=%.4f, Recall=%.4f, F1=%.4f, ROC-AUC=%.4f, PR-AUC=%.4f",
        prec,
        rec,
        f1,
        roc_auc,
        pr_auc,
    )
    return model, metrics


def save_xgboost_artifacts(
    model: XGBClassifier,
    metrics: Dict[str, Any],
    artifacts_dir: str = "models/artifacts",
) -> Dict[str, str]:
    """Saves serialized model, feature definitions, and training metrics."""
    out_dir = Path(artifacts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    joblib_path = out_dir / "xgboost_model.joblib"
    json_path = out_dir / "xgboost_model.json"
    features_path = out_dir / "feature_columns.json"
    metrics_path = out_dir / "xgboost_metrics.json"

    joblib.dump(model, joblib_path)
    model.save_model(json_path)

    with open(features_path, "w") as f:
        json.dump(ALL_ENGINEERED_FEATURE_COLUMNS, f, indent=2)

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("XGBoost artifacts saved to %s", out_dir)
    return {
        "joblib": str(joblib_path),
        "json": str(json_path),
        "features": str(features_path),
        "metrics": str(metrics_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FinStream AI Supervised XGBoost Training Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--samples", type=int, default=10000, help="Number of synthetic samples")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--threshold", type=float, default=0.50, help="Classification probability threshold")
    parser.add_argument("--artifacts-dir", type=str, default="models/artifacts", help="Output directory for artifacts")
    return parser.parse_args()


def main():
    args = parse_args()
    df = generate_synthetic_dataset(num_samples=args.samples, random_seed=args.seed)
    X_train, X_test, y_train, y_test = get_train_test_split(df, random_state=args.seed)

    model, metrics = train_and_evaluate_xgboost(
        X_train,
        X_test,
        y_train,
        y_test,
        threshold=args.threshold,
    )
    save_xgboost_artifacts(model, metrics, artifacts_dir=args.artifacts_dir)


if __name__ == "__main__":
    main()
