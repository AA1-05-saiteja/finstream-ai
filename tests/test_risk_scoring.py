"""
FinStream AI - Unit Tests for Hybrid Risk Scoring & Level Assignment
Validates normalization bounds, weight constraints, hybrid calculations, and categorical levels.
"""

import pytest
from models.risk_scoring import (
    assign_risk_level,
    build_risk_assessment_record,
    calculate_hybrid_risk_score,
    normalize_isolation_forest_score,
)


def test_isolation_forest_score_normalization():
    """Verify raw inverted Isolation Forest scores are bounded within [0.0, 1.0]."""
    # Strongly inlier/normal score
    assert normalize_isolation_forest_score(-0.25, min_bound=-0.15, max_bound=0.25) == 0.0
    # Strongly outlier/anomalous score
    assert normalize_isolation_forest_score(0.35, min_bound=-0.15, max_bound=0.25) == 1.0
    # Midpoint score
    assert normalize_isolation_forest_score(0.05, min_bound=-0.15, max_bound=0.25) == 0.50


def test_hybrid_risk_score_calculation():
    """Verify hybrid risk formula: 0.70 * XGBoost + 0.30 * IF_norm."""
    # Test case 1: P_xgb=0.80, IF_norm=0.60 -> 0.70*0.80 + 0.30*0.60 = 0.56 + 0.18 = 0.74
    score1 = calculate_hybrid_risk_score(0.80, 0.60, weight_xgb=0.70, weight_if=0.30)
    assert score1 == 0.74

    # Test case 2: P_xgb=0.10, IF_norm=0.20 -> 0.70*0.10 + 0.30*0.20 = 0.07 + 0.06 = 0.13
    score2 = calculate_hybrid_risk_score(0.10, 0.20, weight_xgb=0.70, weight_if=0.30)
    assert score2 == 0.13


def test_invalid_weights_rejected():
    """Verify weights that do not sum to 1.0 raise ValueError."""
    with pytest.raises(ValueError):
        calculate_hybrid_risk_score(0.5, 0.5, weight_xgb=0.8, weight_if=0.4)


def test_risk_level_assignments():
    """Verify categorical risk levels at exact boundary conditions."""
    # LOW: < 0.30
    assert assign_risk_level(0.00) == "LOW"
    assert assign_risk_level(0.10) == "LOW"
    assert assign_risk_level(0.2999) == "LOW"

    # MEDIUM: 0.30 to < 0.70
    assert assign_risk_level(0.30) == "MEDIUM"
    assert assign_risk_level(0.50) == "MEDIUM"
    assert assign_risk_level(0.6999) == "MEDIUM"

    # HIGH: >= 0.70
    assert assign_risk_level(0.70) == "HIGH"
    assert assign_risk_level(0.95) == "HIGH"
    assert assign_risk_level(1.00) == "HIGH"


def test_build_risk_assessment_record():
    """Verify end-to-end record assembly."""
    record = build_risk_assessment_record(
        transaction_id="TX999",
        account_id="ACC999",
        amount=85000.0,
        xgboost_prob=0.92,
        raw_if_score=0.15,
        low_threshold=0.30,
        high_threshold=0.70,
    )
    assert record["transaction_id"] == "TX999"
    assert record["amount"] == 85000.0
    assert record["xgboost_probability"] == 0.92
    assert record["risk_level"] == "HIGH"
    assert 0.0 <= record["hybrid_risk_score"] <= 1.0
