"""
FinStream AI - Unit Tests for SHAP Explainability Engine
Validates TreeExplainer generation, feature ranking, direction assignment, and top-N truncation.
"""

from pathlib import Path
import joblib
import numpy as np
import pytest
from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS
from models.shap_explainer import TransactionSHAPExplainer, create_shap_explainer


@pytest.fixture
def trained_xgb_model():
    model_path = Path("models/artifacts/xgboost_model.joblib")
    if not model_path.exists():
        pytest.skip("XGBoost artifact not found on disk")
    return joblib.load(model_path)


def test_shap_explainer_initialization(trained_xgb_model):
    """Verify TransactionSHAPExplainer initializes with model and feature list."""
    explainer = create_shap_explainer(
        model=trained_xgb_model,
        feature_names=ALL_ENGINEERED_FEATURE_COLUMNS,
    )
    assert explainer is not None
    assert explainer.model is trained_xgb_model
    assert explainer.feature_names == ALL_ENGINEERED_FEATURE_COLUMNS


def test_shap_explanation_generation_and_ranking(trained_xgb_model):
    """Verify SHAP explanation produces ranked top-N features with valid directions."""
    explainer = create_shap_explainer(
        model=trained_xgb_model,
        feature_names=ALL_ENGINEERED_FEATURE_COLUMNS,
    )

    # Synthetic anomalous vector: high amount, velocity burst
    sample_features = {col: 0.0 for col in ALL_ENGINEERED_FEATURE_COLUMNS}
    sample_features["amount"] = 85000.0
    sample_features["log_amount"] = 11.35
    sample_features["transaction_count_1m"] = 6
    sample_features["amount_deviation_from_recent_avg"] = 80000.0

    top_shap = explainer.explain_transaction(sample_features, top_n=5)

    assert len(top_shap) == 5
    for item in top_shap:
        assert "feature" in item
        assert "feature_value" in item
        assert "shap_value" in item
        assert "absolute_shap_value" in item
        assert "direction" in item
        assert item["direction"] in ["increases_anomaly", "decreases_anomaly", "neutral"]

    # Verify descending ordering by absolute SHAP value
    abs_values = [item["absolute_shap_value"] for item in top_shap]
    assert abs_values == sorted(abs_values, reverse=True)
