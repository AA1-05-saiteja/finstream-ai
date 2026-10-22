"""
FinStream AI - Complete Model Training, Benchmarking & Report Generator
Orchestrates synthetic dataset generation, dual-model training (XGBoost + Isolation Forest),
artifact serialization, and evaluation report creation.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
import pandas as pd

# Ensure project root is in sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS, FEATURE_METADATA
from models.train_isolation_forest import (
    save_isolation_forest_artifacts,
    train_and_evaluate_isolation_forest,
)
from models.train_xgboost import save_xgboost_artifacts, train_and_evaluate_xgboost
from models.training_data import generate_synthetic_dataset, get_train_test_split

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("train_all")


def generate_markdown_report(
    summary_data: Dict[str, Any],
    output_path: Path,
) -> None:
    """Generates a comprehensive Markdown evaluation report."""
    dataset_info = summary_data["dataset"]
    xgb_info = summary_data["xgboost"]
    if_info = summary_data["isolation_forest"]

    md = f"""# FinStream AI — Phase 6 Model Training & Evaluation Report

**Generated At (UTC)**: {summary_data["timestamp"]}  
**Random Seed**: {dataset_info["random_seed"]}  
**Evaluation Scope**: Offline Academic Benchmark against Synthetic Ground Truth  

---

## 1. Dataset & Ground-Truth Methodology

* **Total Records**: {dataset_info["total_samples"]:,}
* **Feature Count**: {dataset_info["num_features"]}
* **Normal Records (y=0)**: {dataset_info["normal_samples"]:,} ({dataset_info["normal_pct"]}%)
* **Synthetic Anomalies (y=1)**: {dataset_info["anomaly_samples"]:,} ({dataset_info["anomaly_pct"]}%)
* **Train / Test Split**: {dataset_info["train_samples"]:,} train / {dataset_info["test_samples"]:,} test (80/20 Stratified)

### Labeling Strategy
Labels are assigned deterministically based on synthetic scenario patterns:
* `y = 0` (Normal baseline): Gaussian spending around account mean, preferred merchants, known devices, home city.
* `y = 1` (Synthetic anomalies): High-amount spikes (> ₹65,000), 1-minute velocity bursts, unseen devices, merchant shifts, and distant city displacements.

*Target Leakage Prevention*: Identifiers (`transaction_id`, `account_id`, `merchant_id`, `device_id`, `city`, `timestamp`) and scenario tags (`scenario_label`) were strictly excluded from feature matrix $X$.

---

## 2. Model Performance Comparison

| Evaluation Metric | Supervised XGBoost | Unsupervised Isolation Forest |
| :--- | :---: | :---: |
| **Accuracy** | {xgb_info["accuracy"]:.4f} | {if_info["accuracy"]:.4f} |
| **Precision** | {xgb_info["precision"]:.4f} | {if_info["precision"]:.4f} |
| **Recall** | {xgb_info["recall"]:.4f} | {if_info["recall"]:.4f} |
| **F1-Score** | {xgb_info["f1_score"]:.4f} | {if_info["f1_score"]:.4f} |
| **ROC-AUC** | {xgb_info["roc_auc"]:.4f} | {if_info["roc_auc"]:.4f} |
| **PR-AUC** | {xgb_info["pr_auc"]:.4f} | {if_info["pr_auc"]:.4f} |

---

## 3. Supervised Model: XGBoost Classifier

### Hyperparameters
```json
{json.dumps(xgb_info["parameters"], indent=2)}
```

### Confusion Matrix (Test Set, N={dataset_info["test_samples"]:,})
* **True Negatives (TN)**: {xgb_info["confusion_matrix"]["tn"]}
* **False Positives (FP)**: {xgb_info["confusion_matrix"]["fp"]}
* **False Negatives (FN)**: {xgb_info["confusion_matrix"]["fn"]}
* **True Positives (TP)**: {xgb_info["confusion_matrix"]["tp"]}

---

## 4. Unsupervised Model: Isolation Forest

### Hyperparameters
```json
{json.dumps(if_info["parameters"], indent=2)}
```

### Anomaly Score Interpretation
* Scikit-Learn's raw `decision_function` outputs negative values for outliers and positive for inliers.
* For consistent benchmark alignment, scores are inverted ($\\text{{anomaly\\_score}} = -\\text{{decision\\_function}}(X)$), so higher values represent stronger anomaly likelihood.

### Confusion Matrix (Test Set, N={dataset_info["test_samples"]:,})
* **True Negatives (TN)**: {if_info["confusion_matrix"]["tn"]}
* **False Positives (FP)**: {if_info["confusion_matrix"]["fp"]}
* **False Negatives (FN)**: {if_info["confusion_matrix"]["fn"]}
* **True Positives (TP)**: {if_info["confusion_matrix"]["tp"]}

---

## 5. Limitations & Academic Disclaimer

1. **Synthetic Ground Truth**: The models were trained and benchmarked strictly on synthetically generated transactions and scenario distributions. Performance figures reflect pattern separation in synthetic data rather than real banking environments.
2. **Offline Evaluation**: Metrics are measured on held-out test splits without streaming latency or database write contention.
3. **No Automated Blocking**: FinStream AI is designed as a decision-support system to flag anomalous patterns for human analyst review.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    logger.info("Markdown evaluation report written to %s", output_path)


def run_full_training_pipeline(
    samples: int = 10000,
    seed: int = 42,
    artifacts_dir: str = "models/artifacts",
    reports_dir: str = "reports",
) -> Dict[str, Any]:
    """Runs data generation, model fitting, serialization, and report creation."""
    start_time = time.time()
    artifacts_path = Path(artifacts_dir)
    reports_path = Path(reports_dir)
    artifacts_path.mkdir(parents=True, exist_ok=True)
    reports_path.mkdir(parents=True, exist_ok=True)

    # 1. Generate synthetic dataset
    df = generate_synthetic_dataset(num_samples=samples, random_seed=seed)
    X_train, X_test, y_train, y_test = get_train_test_split(df, random_state=seed)

    # 2. Train XGBoost
    xgb_model, xgb_metrics = train_and_evaluate_xgboost(X_train, X_test, y_train, y_test)
    save_xgboost_artifacts(xgb_model, xgb_metrics, artifacts_dir=artifacts_dir)

    # 3. Train Isolation Forest (Unsupervised - no y_train)
    if_model, if_metrics = train_and_evaluate_isolation_forest(X_train, X_test, y_test, params={"random_state": seed})
    save_isolation_forest_artifacts(if_model, if_metrics, artifacts_dir=artifacts_dir)

    # 4. Compile metadata and summary
    normal_count = int((df["is_anomaly"] == 0).sum())
    anomaly_count = int((df["is_anomaly"] == 1).sum())

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_training_seconds": round(time.time() - start_time, 2),
        "dataset": {
            "total_samples": len(df),
            "num_features": len(ALL_ENGINEERED_FEATURE_COLUMNS),
            "normal_samples": normal_count,
            "normal_pct": round(normal_count / len(df) * 100, 2),
            "anomaly_samples": anomaly_count,
            "anomaly_pct": round(anomaly_count / len(df) * 100, 2),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "random_seed": seed,
        },
        "feature_columns": ALL_ENGINEERED_FEATURE_COLUMNS,
        "xgboost": xgb_metrics,
        "isolation_forest": if_metrics,
    }

    # Save training metadata
    metadata_path = artifacts_path / "training_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Save JSON report
    json_report_path = reports_path / "phase6_evaluation.json"
    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Save Markdown report
    md_report_path = reports_path / "phase6_evaluation.md"
    generate_markdown_report(summary, md_report_path)

    logger.info("Complete training pipeline executed successfully in %.2fs", time.time() - start_time)
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="FinStream AI Dual-Model Training and Evaluation Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--samples", type=int, default=10000, help="Total synthetic training samples")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--artifacts-dir", type=str, default="models/artifacts", help="Artifact directory")
    parser.add_argument("--reports-dir", type=str, default="reports", help="Reports directory")
    args = parser.parse_args()

    run_full_training_pipeline(
        samples=args.samples,
        seed=args.seed,
        artifacts_dir=args.artifacts_dir,
        reports_dir=args.reports_dir,
    )


if __name__ == "__main__":
    main()
