"""
FinStream AI - Unit Tests for Real-Time Prediction & Inference Pipeline
Validates artifact loading, feature alignment, dual-model scoring, and SHAP integration.
"""

from pathlib import Path
import pytest
from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS
from models.predict import ModelInferenceEngine, load_inference_engine


def test_inference_engine_loading():
    """Verify ModelInferenceEngine loads artifacts from models/artifacts."""
    engine = load_inference_engine()
    assert engine.xgb_model is not None
    assert engine.if_model is not None
    assert len(engine.feature_columns) == len(ALL_ENGINEERED_FEATURE_COLUMNS)
    assert engine.shap_explainer is not None


def test_missing_artifacts_raises_file_not_found():
    """Verify loading from nonexistent directory raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        ModelInferenceEngine(artifacts_dir="models/nonexistent_dir")


def test_predict_single_normal_transaction():
    """Verify inference on a baseline normal transaction."""
    engine = load_inference_engine()

    normal_tx = {
        "transaction_id": "TX_TEST_001",
        "account_id": "ACC_TEST_001",
        "amount": 750.0,
        "log_amount": 6.62,
        "transaction_count_1m": 1,
        "transaction_count_5m": 1,
        "transaction_count_1h": 2,
        "total_amount_5m": 750.0,
        "total_amount_1h": 1500.0,
        "average_amount_5m": 750.0,
        "average_amount_1h": 750.0,
        "maximum_amount_1h": 750.0,
        "minimum_amount_1h": 750.0,
        "amount_deviation_from_recent_avg": 0.0,
        "amount_ratio_to_recent_avg": 1.0,
        "merchant_transaction_count_1h": 1,
        "device_transaction_count_1h": 2,
        "city_transaction_count_1h": 2,
        "channel_transaction_count_1h": 1,
        "unique_device_count_1h": 1,
        "unique_merchant_count_1h": 2,
        "unique_city_count_1h": 1,
        "unique_channel_count_1h": 1,
        "known_device_flag": 1,
        "new_city_flag": 0,
    }

    result = engine.predict_single(normal_tx, explain=False)

    assert result["transaction_id"] == "TX_TEST_001"
    assert result["account_id"] == "ACC_TEST_001"
    assert result["amount"] == 750.0
    assert 0.0 <= result["xgboost_probability"] <= 1.0
    assert 0.0 <= result["isolation_forest_normalized"] <= 1.0
    assert 0.0 <= result["hybrid_risk_score"] <= 1.0
    assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "top_shap_features" not in result


def test_predict_single_with_shap_explanation():
    """Verify inference on a high-risk anomalous transaction includes SHAP features."""
    engine = load_inference_engine()

    anomalous_tx = {
        "transaction_id": "TX_TEST_002",
        "account_id": "ACC_TEST_002",
        "amount": 95000.0,
        "log_amount": 11.46,
        "transaction_count_1m": 6,
        "transaction_count_5m": 8,
        "transaction_count_1h": 12,
        "total_amount_5m": 120000.0,
        "total_amount_1h": 150000.0,
        "average_amount_5m": 15000.0,
        "average_amount_1h": 12500.0,
        "maximum_amount_1h": 95000.0,
        "minimum_amount_1h": 500.0,
        "amount_deviation_from_recent_avg": 82500.0,
        "amount_ratio_to_recent_avg": 7.6,
        "merchant_transaction_count_1h": 1,
        "device_transaction_count_1h": 1,
        "city_transaction_count_1h": 1,
        "channel_transaction_count_1h": 6,
        "unique_device_count_1h": 3,
        "unique_merchant_count_1h": 4,
        "unique_city_count_1h": 2,
        "unique_channel_count_1h": 1,
        "known_device_flag": 0,
        "new_city_flag": 1,
    }

    result = engine.predict_single(anomalous_tx, explain=True, top_n_shap=4)

    assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "top_shap_features" in result
    assert len(result["top_shap_features"]) == 4
    for feat in result["top_shap_features"]:
        assert "feature" in feat
        assert "direction" in feat
        assert "shap_value" in feat
