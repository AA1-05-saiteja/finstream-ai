"""
FinStream AI - Unit Tests for Feature Definitions & Formulas
Validates feature constants, log-transformations, deviation, and ratio calculations.
"""

import math
import pytest
from features.feature_definitions import (
    ALL_ENGINEERED_FEATURE_COLUMNS,
    FEATURE_AMOUNT,
    FEATURE_AMOUNT_DEV_RECENT_AVG,
    FEATURE_AMOUNT_RATIO_RECENT_AVG,
    FEATURE_KNOWN_DEVICE_FLAG,
    FEATURE_LOG_AMOUNT,
    FEATURE_METADATA,
    FEATURE_NEW_CITY_FLAG,
    FEATURE_TX_COUNT_1H,
    FEATURE_TX_COUNT_1M,
    FEATURE_TX_COUNT_5M,
    calculate_amount_deviation,
    calculate_amount_ratio,
    calculate_log_amount,
)


def test_feature_columns_completeness():
    """Verify all 23 engineered feature constants exist and have corresponding metadata."""
    assert len(ALL_ENGINEERED_FEATURE_COLUMNS) == 23
    for col in ALL_ENGINEERED_FEATURE_COLUMNS:
        assert isinstance(col, str)
        assert len(col) > 0
        assert col in FEATURE_METADATA


def test_log_amount_calculation():
    """Verify calculate_log_amount produces accurate ln(1 + amount)."""
    assert calculate_log_amount(0.0) == 0.0
    # log1p(100.0) = ln(101.0) ~= 4.6151
    assert pytest.approx(calculate_log_amount(100.0), rel=1e-3) == round(math.log1p(100.0), 4)

    with pytest.raises(ValueError):
        calculate_log_amount(-10.0)


def test_amount_deviation_calculation():
    """Verify calculate_amount_deviation calculates difference from recent average."""
    # Current amount 1500, average 1000 -> deviation +500
    assert calculate_amount_deviation(1500.0, 1000.0) == 500.0
    # Current amount 500, average 1000 -> deviation -500
    assert calculate_amount_deviation(500.0, 1000.0) == -500.0
    # Zero or missing historical average fallback
    assert calculate_amount_deviation(1500.0, 0.0) == 0.0


def test_amount_ratio_calculation():
    """Verify calculate_amount_ratio calculates ratio safely with zero-division fallback."""
    # Current amount 2500, average 1000 -> ratio 2.5
    assert calculate_amount_ratio(2500.0, 1000.0) == 2.5
    # Current amount 500, average 1000 -> ratio 0.5
    assert calculate_amount_ratio(500.0, 1000.0) == 0.5
    # Zero historical average fallback returns 1.0 (neutral baseline)
    assert calculate_amount_ratio(1500.0, 0.0) == 1.0
