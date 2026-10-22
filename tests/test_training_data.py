"""
FinStream AI - Unit Tests for Synthetic Training Dataset Generator
Validates data generation, schema integrity, ground-truth label validity,
target leakage prevention, and train/test splits.
"""

import pandas as pd
import pytest
from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS
from models.training_data import (
    generate_synthetic_dataset,
    get_train_test_split,
    prepare_feature_matrix,
)


def test_synthetic_dataset_generation():
    """Verify dataset generates requested sample size with expected columns."""
    df = generate_synthetic_dataset(num_samples=200, num_accounts=20, random_seed=42)
    assert len(df) == 200
    assert "is_anomaly" in df.columns
    assert "scenario_label" in df.columns

    # Verify all 23 engineered features are present in dataset
    for col in ALL_ENGINEERED_FEATURE_COLUMNS:
        assert col in df.columns


def test_deterministic_data_generation_with_seed():
    """Verify identical seeds produce identical datasets."""
    df1 = generate_synthetic_dataset(num_samples=100, num_accounts=10, random_seed=99)
    df2 = generate_synthetic_dataset(num_samples=100, num_accounts=10, random_seed=99)

    pd.testing.assert_frame_equal(df1, df2)


def test_target_leakage_prevention():
    """Verify feature matrix X contains strictly engineered numeric features and no identifiers/labels."""
    df = generate_synthetic_dataset(num_samples=100, num_accounts=10, random_seed=123)
    X, y = prepare_feature_matrix(df)

    assert X.shape[1] == len(ALL_ENGINEERED_FEATURE_COLUMNS)
    assert list(X.columns) == ALL_ENGINEERED_FEATURE_COLUMNS

    # Ensure no leakage columns are in X
    leakage_columns = [
        "transaction_id",
        "account_id",
        "merchant_id",
        "device_id",
        "city",
        "channel",
        "timestamp",
        "scenario_label",
        "is_anomaly",
        "target",
    ]
    for col in leakage_columns:
        assert col not in X.columns

    # Verify target y is binary
    assert set(y.unique()).issubset({0, 1})


def test_stratified_train_test_split():
    """Verify train/test split maintains stratified class ratios."""
    df = generate_synthetic_dataset(num_samples=300, num_accounts=20, random_seed=42)
    X_train, X_test, y_train, y_test = get_train_test_split(df, test_size=0.20, random_state=42)

    assert len(X_train) == 240
    assert len(X_test) == 60

    train_ratio = y_train.mean()
    test_ratio = y_test.mean()
    # Stratified split should keep anomaly ratio within close tolerance
    assert abs(train_ratio - test_ratio) < 0.05
