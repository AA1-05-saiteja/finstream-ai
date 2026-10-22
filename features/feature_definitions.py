"""
FinStream AI - Feature Definitions & Constants
Defines feature schema schemas, column names, transformation definitions,
and documentation for real-time feature engineering.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# =====================================================================
# Feature Column Identifiers
# =====================================================================

# 1. Transaction Amount Features
FEATURE_AMOUNT = "amount"
FEATURE_LOG_AMOUNT = "log_amount"

# 2. Velocity Features (Event-Time Rolling Windows)
FEATURE_TX_COUNT_1M = "transaction_count_1m"
FEATURE_TX_COUNT_5M = "transaction_count_5m"
FEATURE_TX_COUNT_1H = "transaction_count_1h"

# 3. Spending Features
FEATURE_TOTAL_AMOUNT_5M = "total_amount_5m"
FEATURE_TOTAL_AMOUNT_1H = "total_amount_1h"
FEATURE_AVG_AMOUNT_5M = "average_amount_5m"
FEATURE_AVG_AMOUNT_1H = "average_amount_1h"
FEATURE_MAX_AMOUNT_1H = "maximum_amount_1h"
FEATURE_MIN_AMOUNT_1H = "minimum_amount_1h"

# 4. Amount Deviation Features
FEATURE_AMOUNT_DEV_RECENT_AVG = "amount_deviation_from_recent_avg"
FEATURE_AMOUNT_RATIO_RECENT_AVG = "amount_ratio_to_recent_avg"

# 5. Entity Frequency Features
FEATURE_MERCHANT_TX_COUNT_1H = "merchant_transaction_count_1h"
FEATURE_DEVICE_TX_COUNT_1H = "device_transaction_count_1h"
FEATURE_CITY_TX_COUNT_1H = "city_transaction_count_1h"
FEATURE_CHANNEL_TX_COUNT_1H = "channel_transaction_count_1h"

# 6. Behavioral Cardinality & Diversity Features
FEATURE_UNIQUE_DEVICE_COUNT_1H = "unique_device_count_1h"
FEATURE_UNIQUE_MERCHANT_COUNT_1H = "unique_merchant_count_1h"
FEATURE_UNIQUE_CITY_COUNT_1H = "unique_city_count_1h"
FEATURE_UNIQUE_CHANNEL_COUNT_1H = "unique_channel_count_1h"

# 7. Flags
FEATURE_KNOWN_DEVICE_FLAG = "known_device_flag"
FEATURE_NEW_CITY_FLAG = "new_city_flag"


# Ordered list of all engineered feature names for ML readiness
ALL_ENGINEERED_FEATURE_COLUMNS: List[str] = [
    FEATURE_AMOUNT,
    FEATURE_LOG_AMOUNT,
    FEATURE_TX_COUNT_1M,
    FEATURE_TX_COUNT_5M,
    FEATURE_TX_COUNT_1H,
    FEATURE_TOTAL_AMOUNT_5M,
    FEATURE_TOTAL_AMOUNT_1H,
    FEATURE_AVG_AMOUNT_5M,
    FEATURE_AVG_AMOUNT_1H,
    FEATURE_MAX_AMOUNT_1H,
    FEATURE_MIN_AMOUNT_1H,
    FEATURE_AMOUNT_DEV_RECENT_AVG,
    FEATURE_AMOUNT_RATIO_RECENT_AVG,
    FEATURE_MERCHANT_TX_COUNT_1H,
    FEATURE_DEVICE_TX_COUNT_1H,
    FEATURE_CITY_TX_COUNT_1H,
    FEATURE_CHANNEL_TX_COUNT_1H,
    FEATURE_UNIQUE_DEVICE_COUNT_1H,
    FEATURE_UNIQUE_MERCHANT_COUNT_1H,
    FEATURE_UNIQUE_CITY_COUNT_1H,
    FEATURE_UNIQUE_CHANNEL_COUNT_1H,
    FEATURE_KNOWN_DEVICE_FLAG,
    FEATURE_NEW_CITY_FLAG,
]


# Metadata describing each feature
FEATURE_METADATA: Dict[str, Dict[str, Any]] = {
    FEATURE_AMOUNT: {
        "category": "amount",
        "description": "Raw transaction amount in INR",
        "type": "float",
    },
    FEATURE_LOG_AMOUNT: {
        "category": "amount",
        "description": "Log1p-transformed transaction amount (ln(1 + amount))",
        "type": "float",
    },
    FEATURE_TX_COUNT_1M: {
        "category": "velocity",
        "description": "Number of transactions for account in previous 1 minute",
        "type": "int",
    },
    FEATURE_TX_COUNT_5M: {
        "category": "velocity",
        "description": "Number of transactions for account in previous 5 minutes",
        "type": "int",
    },
    FEATURE_TX_COUNT_1H: {
        "category": "velocity",
        "description": "Number of transactions for account in previous 1 hour",
        "type": "int",
    },
    FEATURE_TOTAL_AMOUNT_5M: {
        "category": "spending",
        "description": "Sum of transaction amounts for account in previous 5 minutes",
        "type": "float",
    },
    FEATURE_TOTAL_AMOUNT_1H: {
        "category": "spending",
        "description": "Sum of transaction amounts for account in previous 1 hour",
        "type": "float",
    },
    FEATURE_AVG_AMOUNT_5M: {
        "category": "spending",
        "description": "Average transaction amount for account in previous 5 minutes",
        "type": "float",
    },
    FEATURE_AVG_AMOUNT_1H: {
        "category": "spending",
        "description": "Average transaction amount for account in previous 1 hour",
        "type": "float",
    },
    FEATURE_MAX_AMOUNT_1H: {
        "category": "spending",
        "description": "Maximum transaction amount for account in previous 1 hour",
        "type": "float",
    },
    FEATURE_MIN_AMOUNT_1H: {
        "category": "spending",
        "description": "Minimum transaction amount for account in previous 1 hour",
        "type": "float",
    },
    FEATURE_AMOUNT_DEV_RECENT_AVG: {
        "category": "deviation",
        "description": "Difference between current amount and 1-hour average amount (amount - avg_1h)",
        "type": "float",
    },
    FEATURE_AMOUNT_RATIO_RECENT_AVG: {
        "category": "deviation",
        "description": "Ratio of current amount to 1-hour average amount (amount / avg_1h)",
        "type": "float",
    },
    FEATURE_MERCHANT_TX_COUNT_1H: {
        "category": "frequency",
        "description": "Number of transactions with specific merchant by account in previous 1 hour",
        "type": "int",
    },
    FEATURE_DEVICE_TX_COUNT_1H: {
        "category": "frequency",
        "description": "Number of transactions using specific device by account in previous 1 hour",
        "type": "int",
    },
    FEATURE_CITY_TX_COUNT_1H: {
        "category": "frequency",
        "description": "Number of transactions originating from specific city by account in previous 1 hour",
        "type": "int",
    },
    FEATURE_CHANNEL_TX_COUNT_1H: {
        "category": "frequency",
        "description": "Number of transactions via specific channel by account in previous 1 hour",
        "type": "int",
    },
    FEATURE_UNIQUE_DEVICE_COUNT_1H: {
        "category": "cardinality",
        "description": "Count of distinct devices used by account in previous 1 hour",
        "type": "int",
    },
    FEATURE_UNIQUE_MERCHANT_COUNT_1H: {
        "category": "cardinality",
        "description": "Count of distinct merchants visited by account in previous 1 hour",
        "type": "int",
    },
    FEATURE_UNIQUE_CITY_COUNT_1H: {
        "category": "cardinality",
        "description": "Count of distinct cities visited by account in previous 1 hour",
        "type": "int",
    },
    FEATURE_UNIQUE_CHANNEL_COUNT_1H: {
        "category": "cardinality",
        "description": "Count of distinct channels used by account in previous 1 hour",
        "type": "int",
    },
    FEATURE_KNOWN_DEVICE_FLAG: {
        "category": "flags",
        "description": "Binary flag (1 = device has been observed before for this account, 0 = new device)",
        "type": "int",
    },
    FEATURE_NEW_CITY_FLAG: {
        "category": "flags",
        "description": "Binary flag (1 = city is different from account's recent cities, 0 = usual city)",
        "type": "int",
    },
}


def calculate_log_amount(amount: float) -> float:
    """
    Computes numerically safe log1p(amount) for strictly positive amounts.
    """
    if amount < 0:
        raise ValueError(f"Amount cannot be negative for log calculation: {amount}")
    return round(math.log1p(float(amount)), 4)


def calculate_amount_deviation(amount: float, avg_amount: float) -> float:
    """
    Computes difference between current amount and historical/recent average.
    If avg_amount <= 0, fallback deviation is 0.0.
    """
    if avg_amount <= 0.0:
        return 0.0
    return round(float(amount) - float(avg_amount), 2)


def calculate_amount_ratio(amount: float, avg_amount: float) -> float:
    """
    Computes ratio of current amount to recent average with safe zero-division handling.
    If avg_amount <= 0, fallback ratio is 1.0 (baseline neutral).
    """
    if avg_amount <= 0.0:
        return 1.0
    return round(float(amount) / float(avg_amount), 4)
