"""
FinStream AI - Unit Tests for XGBoost Training Pipeline
Validates model fitting, probability calibration, metric calculations, and artifact persistence.
"""

from pathlib import Path
import joblib
import numpy as np
import pytest
from models.train_xgboost import save_xgboost_artifacts, train_and_evaluate_xgboost
from models.training_data import generate_synthetic_dataset, get_train_test_split


def test_xgboost_model_training_and_evaluation(tmp_path):
    """Verify XGBoost trains on dataset and outputs valid probabilities, metrics, and artifacts."""
    df = generate_synthetic_dataset(num_samples=300, num_accounts=20, random_seed=42)
    X_train, X_test, y_train, y_test = get_train_test_split(df, random_state=42)

    model, metrics = train_and_evaluate_xgboost(
        X_train,
        X_test,
        y_train,
        y_test,
        params={"n_estimators": 20, "max_depth": 3, "random_state": 42},
    )

    # 1. Verify predictions & probabilities
    probas = model.predict_proba(X_test)[:, 1]
    assert len(probas) == len(X_test)
    assert np.all((probas >= 0.0) & (probas <= 1.0))

    # 2. Verify metric bounds
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["recall"] <= 1.0
    assert 0.0 <= metrics["f1_score"] <= 1.0
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert 0.0 <= metrics["pr_auc"] <= 1.0

    # 3. Verify artifact saving and reloading
    artifacts_dir = tmp_path / "artifacts"
    paths = save_xgboost_artifacts(model, metrics, artifacts_dir=str(artifacts_dir))

    assert Path(paths["joblib"]).exists()
    assert Path(paths["json"]).exists()
    assert Path(paths["features"]).exists()

    loaded_model = joblib.load(paths["joblib"])
    loaded_probas = loaded_model.predict_proba(X_test)[:, 1]
    np.testing.assert_allclose(probas, loaded_probas)
