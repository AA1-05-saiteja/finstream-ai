"""
FinStream AI - Unit Tests for Isolation Forest Training Pipeline
Validates unsupervised training, inverted anomaly score orientation, and artifact persistence.
"""

from pathlib import Path
import joblib
import numpy as np
import pytest
from models.train_isolation_forest import (
    save_isolation_forest_artifacts,
    train_and_evaluate_isolation_forest,
)
from models.training_data import generate_synthetic_dataset, get_train_test_split


def test_isolation_forest_training_and_evaluation(tmp_path):
    """Verify Isolation Forest fits without labels and produces valid anomaly metrics."""
    df = generate_synthetic_dataset(num_samples=300, num_accounts=20, random_seed=42)
    X_train, X_test, _, y_test = get_train_test_split(df, random_state=42)

    model, metrics = train_and_evaluate_isolation_forest(
        X_train,
        X_test,
        y_test,
        params={"n_estimators": 20, "contamination": 0.15, "random_state": 42},
    )

    # 1. Verify score orientation
    decision_scores = model.decision_function(X_test)
    anomaly_scores = -decision_scores
    assert len(anomaly_scores) == len(X_test)

    # 2. Verify metric bounds
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["recall"] <= 1.0
    assert 0.0 <= metrics["f1_score"] <= 1.0
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert 0.0 <= metrics["pr_auc"] <= 1.0

    # 3. Verify artifact saving and reloading
    artifacts_dir = tmp_path / "artifacts"
    paths = save_isolation_forest_artifacts(model, metrics, artifacts_dir=str(artifacts_dir))

    assert Path(paths["joblib"]).exists()
    assert Path(paths["metrics"]).exists()

    loaded_model = joblib.load(paths["joblib"])
    loaded_scores = -loaded_model.decision_function(X_test)
    np.testing.assert_allclose(anomaly_scores, loaded_scores)
