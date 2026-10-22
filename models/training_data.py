"""
FinStream AI - Synthetic Training Dataset Generation & Preparation
Generates labeled synthetic datasets enriched with Phase 5 features for supervised
and unsupervised anomaly detection model training.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# Ensure project root is in sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import settings
from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS
from producer.account_profiles import AccountPool
from producer.scenario_generator import ScenarioGenerator
from streaming.feature_engineering import RealTimeFeatureEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("training_data")

# Ground truth scenario mapping:
# 0 = Normal synthetic baseline
# 1 = Synthetic anomaly scenarios
ANOMALOUS_SCENARIOS = {
    "HIGH_AMOUNT",
    "VELOCITY_SPIKE",
    "NEW_DEVICE",
    "UNUSUAL_MERCHANT",
    "UNUSUAL_LOCATION",
    "RAPID_DEVICE_SWITCH",
}


def generate_synthetic_dataset(
    num_samples: int = 10000,
    num_accounts: int = 300,
    anomaly_ratio: float = 0.10,
    random_seed: int = 42,
) -> pd.DataFrame:
    """
    Generates a synthetic financial transaction dataset with ground-truth anomaly labels
    and real-time sliding window features.
    """
    logger.info(
        "Generating synthetic dataset: %d samples, %d accounts, %.1f%% anomalies, seed=%d",
        num_samples,
        num_accounts,
        anomaly_ratio * 100,
        random_seed,
    )

    account_pool = AccountPool(size=num_accounts, seed=random_seed)
    scenario_gen = ScenarioGenerator(account_pool, seed=random_seed)
    feature_engine = RealTimeFeatureEngine()
    feature_engine.reset()

    # Configure scenario distribution to achieve target anomaly_ratio
    normal_weight = 1.0 - anomaly_ratio
    sub_anomaly_weight = anomaly_ratio / 6.0
    scenario_weights = {
        "normal": normal_weight,
        "high_amount": sub_anomaly_weight,
        "velocity_spike": sub_anomaly_weight,
        "new_device": sub_anomaly_weight,
        "unusual_merchant": sub_anomaly_weight,
        "unusual_location": sub_anomaly_weight,
        "rapid_device_switching": sub_anomaly_weight,
    }

    records: List[Dict] = []
    base_time = datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc)

    while len(records) < num_samples:
        tx_events = scenario_gen.generate_mixed(
            scenario_weights=scenario_weights,
            base_time=base_time,
        )

        for tx in tx_events:
            if len(records) >= num_samples:
                break

            tx_dict = tx.model_dump()
            scenario = tx.scenario_label or "NORMAL"
            is_anomaly = 1 if scenario in ANOMALOUS_SCENARIOS else 0

            # Compute 23 engineered features using state engine
            features = feature_engine.extract_features(tx_dict)

            record = {
                # Identifiers & Metadata (Excluded from X to avoid data leakage)
                "transaction_id": tx.transaction_id,
                "timestamp": tx.timestamp,
                "account_id": tx.account_id,
                "merchant_id": tx.merchant_id,
                "city": tx.city,
                "device_id": tx.device_id,
                "channel": tx.channel.value if hasattr(tx.channel, "value") else str(tx.channel),
                "scenario_label": scenario,
                # Ground-truth synthetic label (y)
                "is_anomaly": is_anomaly,
            }
            # Add all engineered feature values
            record.update(features)
            records.append(record)

    df = pd.DataFrame(records)
    logger.info(
        "Dataset generation complete. Shape: %s | Normal: %d, Anomalies: %d (%.2f%%)",
        df.shape,
        (df["is_anomaly"] == 0).sum(),
        (df["is_anomaly"] == 1).sum(),
        (df["is_anomaly"] == 1).mean() * 100,
    )
    return df


def prepare_feature_matrix(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Separates dataset into clean feature matrix X and target label y.
    Strictly excludes identifiers and scenario tags to prevent target leakage.
    """
    # Verify all engineered columns are present
    missing = [c for c in ALL_ENGINEERED_FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required feature columns: {missing}")

    X = df[ALL_ENGINEERED_FEATURE_COLUMNS].copy()
    # Cast all feature columns to float64 to ensure numerical stability
    for col_name in ALL_ENGINEERED_FEATURE_COLUMNS:
        X[col_name] = pd.to_numeric(X[col_name], errors="coerce").fillna(0.0)

    y = df["is_anomaly"].astype(int)
    return X, y


def get_train_test_split(
    df: pd.DataFrame,
    test_size: float = 0.20,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Performs a stratified, reproducible train/test split.
    """
    X, y = prepare_feature_matrix(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    logger.info(
        "Train/Test split complete: Train=%d (Anomalies: %d), Test=%d (Anomalies: %d)",
        len(X_train),
        y_train.sum(),
        len(X_test),
        y_test.sum(),
    )
    return X_train, X_test, y_train, y_test


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FinStream AI Synthetic Training Dataset Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=10000,
        help="Number of synthetic transaction records to generate",
    )
    parser.add_argument(
        "--accounts",
        type=int,
        default=settings.GENERATOR_ACCOUNTS_POOL,
        help="Number of synthetic accounts in population",
    )
    parser.add_argument(
        "--anomaly-ratio",
        type=float,
        default=0.10,
        help="Target proportion of synthetic anomaly events",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic generation",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/training_data.csv",
        help="Output filepath for generated CSV/Parquet dataset",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    df = generate_synthetic_dataset(
        num_samples=args.samples,
        num_accounts=args.accounts,
        anomaly_ratio=args.anomaly_ratio,
        random_seed=args.seed,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix == ".parquet":
        df.to_parquet(out_path, index=False)
    else:
        df.to_csv(out_path, index=False)

    logger.info("Dataset saved successfully to %s", out_path)


if __name__ == "__main__":
    main()
