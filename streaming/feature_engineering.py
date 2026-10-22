"""
FinStream AI - Real-Time Feature Engineering & Sliding Window State Management
Computes behavioral, velocity, spending, frequency, and cardinality features
over event-time sliding windows.
"""

from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from features.feature_definitions import (
    ALL_ENGINEERED_FEATURE_COLUMNS,
    FEATURE_AMOUNT,
    FEATURE_AMOUNT_DEV_RECENT_AVG,
    FEATURE_AMOUNT_RATIO_RECENT_AVG,
    FEATURE_AVG_AMOUNT_1H,
    FEATURE_AVG_AMOUNT_5M,
    FEATURE_CHANNEL_TX_COUNT_1H,
    FEATURE_CITY_TX_COUNT_1H,
    FEATURE_DEVICE_TX_COUNT_1H,
    FEATURE_KNOWN_DEVICE_FLAG,
    FEATURE_LOG_AMOUNT,
    FEATURE_MAX_AMOUNT_1H,
    FEATURE_MERCHANT_TX_COUNT_1H,
    FEATURE_MIN_AMOUNT_1H,
    FEATURE_NEW_CITY_FLAG,
    FEATURE_TOTAL_AMOUNT_1H,
    FEATURE_TOTAL_AMOUNT_5M,
    FEATURE_TX_COUNT_1H,
    FEATURE_TX_COUNT_1M,
    FEATURE_TX_COUNT_5M,
    FEATURE_UNIQUE_CHANNEL_COUNT_1H,
    FEATURE_UNIQUE_CITY_COUNT_1H,
    FEATURE_UNIQUE_DEVICE_COUNT_1H,
    FEATURE_UNIQUE_MERCHANT_COUNT_1H,
    calculate_amount_deviation,
    calculate_amount_ratio,
    calculate_log_amount,
)


class AccountSlidingWindowState:
    """
    Maintains chronological sliding event-time state for a single account.
    Prunes events older than 1 hour (3600 seconds) relative to the latest event time.
    """

    def __init__(self, account_id: str):
        self.account_id = account_id
        # Deque of tuples: (event_time_dt, amount, merchant_id, merchant_category, city, device_id, channel)
        self.history: deque = deque()
        self.all_seen_devices: Set[str] = set()
        self.all_seen_cities: Set[str] = set()

    def _parse_timestamp(self, ts: Any) -> datetime:
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                return ts.replace(tzinfo=timezone.utc)
            return ts.astimezone(timezone.utc)
        elif isinstance(ts, str):
            clean_ts = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        else:
            return datetime.now(timezone.utc)

    def prune_old_events(self, current_event_time: datetime, max_window_seconds: int = 3600) -> None:
        """Removes historical events that fall outside the 1-hour rolling window."""
        cutoff = current_event_time - timedelta(seconds=max_window_seconds)
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()

    def process_and_extract_features(self, tx_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes all engineered features for the current transaction using historical window state,
        then appends the current transaction to the window.
        """
        amount = float(tx_dict.get("amount", 0.0))
        event_time = self._parse_timestamp(tx_dict.get("timestamp"))
        merchant_id = str(tx_dict.get("merchant_id", ""))
        merchant_category = str(tx_dict.get("merchant_category", ""))
        city = str(tx_dict.get("city", ""))
        device_id = str(tx_dict.get("device_id", ""))
        channel = str(tx_dict.get("channel", ""))

        # 1. Prune window before computing features
        self.prune_old_events(event_time, max_window_seconds=3600)

        # 2. Amount Features
        log_amount = calculate_log_amount(amount)

        # 3. Time cutoffs for 1m and 5m sub-windows
        cutoff_1m = event_time - timedelta(minutes=1)
        cutoff_5m = event_time - timedelta(minutes=5)
        cutoff_1h = event_time - timedelta(hours=1)

        # Aggregation accumulators
        count_1m = 0
        count_5m = 0
        count_1h = len(self.history)

        total_5m = 0.0
        total_1h = 0.0
        amounts_1h = []

        merchant_count_1h = 0
        device_count_1h = 0
        city_count_1h = 0
        channel_count_1h = 0

        unique_devices_1h = set()
        unique_merchants_1h = set()
        unique_cities_1h = set()
        unique_channels_1h = set()

        for (h_time, h_amt, h_merch, h_cat, h_city, h_dev, h_chan) in self.history:
            # 1m window
            if h_time >= cutoff_1m:
                count_1m += 1

            # 5m window
            if h_time >= cutoff_5m:
                count_5m += 1
                total_5m += h_amt

            # 1h window
            total_1h += h_amt
            amounts_1h.append(h_amt)

            if h_merch == merchant_id:
                merchant_count_1h += 1
            if h_dev == device_id:
                device_count_1h += 1
            if h_city == city:
                city_count_1h += 1
            if h_chan == channel:
                channel_count_1h += 1

            unique_devices_1h.add(h_dev)
            unique_merchants_1h.add(h_merch)
            unique_cities_1h.add(h_city)
            unique_channels_1h.add(h_chan)

        # Include current event in rolling totals/counts for features
        # Note: Velocity counts include the incoming transaction (+1)
        count_1m += 1
        count_5m += 1
        count_1h += 1

        total_5m += amount
        total_1h += amount
        amounts_1h.append(amount)

        merchant_count_1h += 1
        device_count_1h += 1
        city_count_1h += 1
        channel_count_1h += 1

        unique_devices_1h.add(device_id)
        unique_merchants_1h.add(merchant_id)
        unique_cities_1h.add(city)
        unique_channels_1h.add(channel)

        avg_amount_5m = round(total_5m / count_5m, 2) if count_5m > 0 else amount
        avg_amount_1h = round(total_1h / count_1h, 2) if count_1h > 0 else amount
        max_amount_1h = max(amounts_1h) if amounts_1h else amount
        min_amount_1h = min(amounts_1h) if amounts_1h else amount

        # Deviation & Ratio from 1-hour rolling baseline
        dev_recent_avg = calculate_amount_deviation(amount, avg_amount_1h)
        ratio_recent_avg = calculate_amount_ratio(amount, avg_amount_1h)

        # Flags: Known device vs. new device
        known_device_flag = 1 if (device_id in self.all_seen_devices or len(self.all_seen_devices) == 0) else 0
        new_city_flag = 1 if (len(self.all_seen_cities) > 0 and city not in self.all_seen_cities) else 0

        # Update historical sets & deque
        self.all_seen_devices.add(device_id)
        self.all_seen_cities.add(city)
        self.history.append((event_time, amount, merchant_id, merchant_category, city, device_id, channel))

        return {
            FEATURE_AMOUNT: amount,
            FEATURE_LOG_AMOUNT: log_amount,
            FEATURE_TX_COUNT_1M: count_1m,
            FEATURE_TX_COUNT_5M: count_5m,
            FEATURE_TX_COUNT_1H: count_1h,
            FEATURE_TOTAL_AMOUNT_5M: round(total_5m, 2),
            FEATURE_TOTAL_AMOUNT_1H: round(total_1h, 2),
            FEATURE_AVG_AMOUNT_5M: avg_amount_5m,
            FEATURE_AVG_AMOUNT_1H: avg_amount_1h,
            FEATURE_MAX_AMOUNT_1H: round(max_amount_1h, 2),
            FEATURE_MIN_AMOUNT_1H: round(min_amount_1h, 2),
            FEATURE_AMOUNT_DEV_RECENT_AVG: dev_recent_avg,
            FEATURE_AMOUNT_RATIO_RECENT_AVG: ratio_recent_avg,
            FEATURE_MERCHANT_TX_COUNT_1H: merchant_count_1h,
            FEATURE_DEVICE_TX_COUNT_1H: device_count_1h,
            FEATURE_CITY_TX_COUNT_1H: city_count_1h,
            FEATURE_CHANNEL_TX_COUNT_1H: channel_count_1h,
            FEATURE_UNIQUE_DEVICE_COUNT_1H: len(unique_devices_1h),
            FEATURE_UNIQUE_MERCHANT_COUNT_1H: len(unique_merchants_1h),
            FEATURE_UNIQUE_CITY_COUNT_1H: len(unique_cities_1h),
            FEATURE_UNIQUE_CHANNEL_COUNT_1H: len(unique_channels_1h),
            FEATURE_KNOWN_DEVICE_FLAG: known_device_flag,
            FEATURE_NEW_CITY_FLAG: new_city_flag,
        }


class RealTimeFeatureEngine:
    """
    High-performance real-time feature engineering engine.
    Maintains per-account sliding window states and enriches transaction streams.
    """

    def __init__(self):
        self.account_states: Dict[str, AccountSlidingWindowState] = {}

    def get_or_create_account_state(self, account_id: str) -> AccountSlidingWindowState:
        if account_id not in self.account_states:
            self.account_states[account_id] = AccountSlidingWindowState(account_id)
        return self.account_states[account_id]

    def extract_features(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts engineered feature dictionary for a single transaction."""
        account_id = str(transaction_data.get("account_id", "UNKNOWN"))
        state = self.get_or_create_account_state(account_id)
        return state.process_and_extract_features(transaction_data)

    def enrich_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a shallow copy of the transaction dictionary merged with all engineered features.
        """
        enriched = dict(transaction_data)
        features = self.extract_features(transaction_data)
        enriched.update(features)
        return enriched

    def reset(self) -> None:
        """Clears all in-memory account states (useful for testing)."""
        self.account_states.clear()


# Global engine instance for streaming processors
feature_engine = RealTimeFeatureEngine()
