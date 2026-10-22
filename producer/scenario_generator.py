"""
FinStream AI - Synthetic Scenario Generator
Generates both normal baseline transactions and configurable suspicious behavioral anomalies.
"""

import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from producer.account_profiles import (
    AccountPool,
    AccountProfile,
    INDIAN_CITIES,
    MERCHANTS_BY_CATEGORY,
)
from producer.transaction_models import (
    Channel,
    MerchantCategory,
    Transaction,
    TransactionType,
)


class ScenarioGenerator:
    """
    Generates synthetic transactions under specified normal or suspicious scenarios.
    """

    def __init__(self, account_pool: AccountPool, seed: Optional[int] = None):
        self.account_pool = account_pool
        self.rng = random.Random(seed)
        self.tx_counter = 0

    def _next_tx_id(self) -> str:
        self.tx_counter += 1
        return f"TX{self.tx_counter:06d}"

    def _get_current_timestamp_str(self, base_time: Optional[datetime] = None) -> str:
        dt = base_time or datetime.now(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _pick_merchant(self, category: str) -> str:
        merchants = MERCHANTS_BY_CATEGORY.get(
            category, [f"MER_GEN_{self.rng.randint(1, 20):03d}"]
        )
        return self.rng.choice(merchants)

    # -------------------------------------------------------------
    # Scenario 1: Normal Transaction
    # -------------------------------------------------------------
    def generate_normal(
        self,
        account: Optional[AccountProfile] = None,
        base_time: Optional[datetime] = None,
    ) -> Transaction:
        acc = account or self.account_pool.sample_account()
        category = self.rng.choice(acc.preferred_categories)
        merchant_id = self._pick_merchant(category)
        city = acc.home_city
        device_id = acc.get_preferred_device(self.rng)
        channel = self.rng.choice(acc.preferred_channels)
        card_present = channel in [Channel.POS, Channel.ATM]
        amount = acc.sample_normal_amount(self.rng)
        tx_type = (
            TransactionType.WITHDRAWAL
            if channel == Channel.ATM
            else TransactionType.PURCHASE
        )

        tx_time = base_time or datetime.now(timezone.utc)
        acc.last_transaction_time = tx_time
        acc.transaction_count += 1

        tx = Transaction(
            transaction_id=self._next_tx_id(),
            timestamp=self._get_current_timestamp_str(tx_time),
            account_id=acc.account_id,
            amount=amount,
            currency="INR",
            merchant_id=merchant_id,
            merchant_category=category,
            city=city,
            device_id=device_id,
            channel=channel,
            card_present=card_present,
            transaction_type=tx_type,
            scenario_label="NORMAL",
        )
        acc.recent_transactions.append(tx)
        return tx

    # -------------------------------------------------------------
    # Scenario 2: Unusually High Amount
    # -------------------------------------------------------------
    def generate_high_amount(
        self,
        account: Optional[AccountProfile] = None,
        base_time: Optional[datetime] = None,
    ) -> Transaction:
        acc = account or self.account_pool.sample_account()
        # Amount significantly exceeds the account's historical profile
        multiplier = self.rng.uniform(12.0, 35.0)
        base_amount = max(acc.avg_amount * multiplier, 65000.0)
        # Cap at realistic synthetic limit
        amount = round(min(base_amount, 350000.0) + self.rng.uniform(10.0, 99.0), 2)

        category = self.rng.choice(
            [MerchantCategory.LUXURY.value, MerchantCategory.ELECTRONICS.value, MerchantCategory.TRAVEL.value]
        )
        merchant_id = self._pick_merchant(category)
        device_id = acc.get_preferred_device(self.rng)
        channel = Channel.ONLINE

        tx_time = base_time or datetime.now(timezone.utc)
        acc.last_transaction_time = tx_time
        acc.transaction_count += 1

        tx = Transaction(
            transaction_id=self._next_tx_id(),
            timestamp=self._get_current_timestamp_str(tx_time),
            account_id=acc.account_id,
            amount=amount,
            currency="INR",
            merchant_id=merchant_id,
            merchant_category=category,
            city=acc.home_city,
            device_id=device_id,
            channel=channel,
            card_present=False,
            transaction_type=TransactionType.PURCHASE,
            scenario_label="HIGH_AMOUNT",
        )
        acc.recent_transactions.append(tx)
        return tx

    # -------------------------------------------------------------
    # Scenario 3: Velocity Spike (Multiple Rapid Transactions)
    # -------------------------------------------------------------
    def generate_velocity_spike(
        self,
        account: Optional[AccountProfile] = None,
        count: int = 4,
        base_time: Optional[datetime] = None,
    ) -> List[Transaction]:
        acc = account or self.account_pool.sample_account()
        start_time = base_time or datetime.now(timezone.utc)
        transactions = []

        for i in range(count):
            # Timestamps are 1-4 seconds apart
            tx_time = start_time + timedelta(seconds=i * self.rng.randint(1, 4))
            category = self.rng.choice(acc.preferred_categories)
            merchant_id = self._pick_merchant(category)
            # Escalating amounts
            multiplier = 1.0 + (i * 0.8)
            amount = round(acc.sample_normal_amount(self.rng) * multiplier + self.rng.uniform(10.0, 50.0), 2)

            acc.last_transaction_time = tx_time
            acc.transaction_count += 1

            tx = Transaction(
                transaction_id=self._next_tx_id(),
                timestamp=self._get_current_timestamp_str(tx_time),
                account_id=acc.account_id,
                amount=amount,
                currency="INR",
                merchant_id=merchant_id,
                merchant_category=category,
                city=acc.home_city,
                device_id=acc.get_preferred_device(self.rng),
                channel=Channel.ONLINE,
                card_present=False,
                transaction_type=TransactionType.PURCHASE,
                scenario_label="VELOCITY_SPIKE",
            )
            acc.recent_transactions.append(tx)
            transactions.append(tx)

        return transactions

    # -------------------------------------------------------------
    # Scenario 4: New Device
    # -------------------------------------------------------------
    def generate_new_device(
        self,
        account: Optional[AccountProfile] = None,
        base_time: Optional[datetime] = None,
    ) -> Transaction:
        acc = account or self.account_pool.sample_account()
        unseen_device = f"DEV_UNSEEN_{self.rng.randint(10000, 99999)}"
        category = self.rng.choice(acc.preferred_categories)
        merchant_id = self._pick_merchant(category)
        amount = round(acc.sample_normal_amount(self.rng) * self.rng.uniform(2.5, 6.0), 2)

        tx_time = base_time or datetime.now(timezone.utc)
        acc.last_transaction_time = tx_time
        acc.transaction_count += 1

        tx = Transaction(
            transaction_id=self._next_tx_id(),
            timestamp=self._get_current_timestamp_str(tx_time),
            account_id=acc.account_id,
            amount=amount,
            currency="INR",
            merchant_id=merchant_id,
            merchant_category=category,
            city=acc.home_city,
            device_id=unseen_device,
            channel=Channel.ONLINE,
            card_present=False,
            transaction_type=TransactionType.PURCHASE,
            scenario_label="NEW_DEVICE",
        )
        acc.recent_transactions.append(tx)
        return tx

    # -------------------------------------------------------------
    # Scenario 5: Unusual Merchant Category
    # -------------------------------------------------------------
    def generate_unusual_merchant(
        self,
        account: Optional[AccountProfile] = None,
        base_time: Optional[datetime] = None,
    ) -> Transaction:
        acc = account or self.account_pool.sample_account()
        # Select category not in account preferences
        non_preferred = [
            c.value for c in MerchantCategory if c.value not in acc.preferred_categories
        ]
        category = (
            self.rng.choice(non_preferred)
            if non_preferred
            else MerchantCategory.LUXURY.value
        )
        merchant_id = self._pick_merchant(category)
        amount = round(acc.avg_amount * self.rng.uniform(3.0, 7.0), 2)

        tx_time = base_time or datetime.now(timezone.utc)
        acc.last_transaction_time = tx_time
        acc.transaction_count += 1

        tx = Transaction(
            transaction_id=self._next_tx_id(),
            timestamp=self._get_current_timestamp_str(tx_time),
            account_id=acc.account_id,
            amount=amount,
            currency="INR",
            merchant_id=merchant_id,
            merchant_category=category,
            city=acc.home_city,
            device_id=acc.get_preferred_device(self.rng),
            channel=Channel.ONLINE,
            card_present=False,
            transaction_type=TransactionType.PURCHASE,
            scenario_label="UNUSUAL_MERCHANT",
        )
        acc.recent_transactions.append(tx)
        return tx

    # -------------------------------------------------------------
    # Scenario 6: Unusual Location / City
    # -------------------------------------------------------------
    def generate_unusual_location(
        self,
        account: Optional[AccountProfile] = None,
        base_time: Optional[datetime] = None,
    ) -> Transaction:
        acc = account or self.account_pool.sample_account()
        other_cities = [c for c in INDIAN_CITIES if c != acc.home_city]
        distant_city = self.rng.choice(other_cities)
        category = self.rng.choice(acc.preferred_categories)
        merchant_id = self._pick_merchant(category)
        amount = acc.sample_normal_amount(self.rng)

        tx_time = base_time or datetime.now(timezone.utc)
        acc.last_transaction_time = tx_time
        acc.transaction_count += 1

        tx = Transaction(
            transaction_id=self._next_tx_id(),
            timestamp=self._get_current_timestamp_str(tx_time),
            account_id=acc.account_id,
            amount=amount,
            currency="INR",
            merchant_id=merchant_id,
            merchant_category=category,
            city=distant_city,
            device_id=acc.get_preferred_device(self.rng),
            channel=Channel.POS,
            card_present=True,
            transaction_type=TransactionType.PURCHASE,
            scenario_label="UNUSUAL_LOCATION",
        )
        acc.recent_transactions.append(tx)
        return tx

    # -------------------------------------------------------------
    # Scenario 7: Rapid Device Switching
    # -------------------------------------------------------------
    def generate_rapid_device_switching(
        self,
        account: Optional[AccountProfile] = None,
        count: int = 3,
        base_time: Optional[datetime] = None,
    ) -> List[Transaction]:
        acc = account or self.account_pool.sample_account()
        start_time = base_time or datetime.now(timezone.utc)
        transactions = []

        for i in range(count):
            tx_time = start_time + timedelta(seconds=i * 2)
            switching_device = f"DEV_SWITCH_{i+1}_{self.rng.randint(1000, 9999)}"
            category = self.rng.choice(acc.preferred_categories)
            merchant_id = self._pick_merchant(category)
            amount = round(acc.sample_normal_amount(self.rng) * (1.2 + (i * 0.5)), 2)

            acc.last_transaction_time = tx_time
            acc.transaction_count += 1

            tx = Transaction(
                transaction_id=self._next_tx_id(),
                timestamp=self._get_current_timestamp_str(tx_time),
                account_id=acc.account_id,
                amount=amount,
                currency="INR",
                merchant_id=merchant_id,
                merchant_category=category,
                city=acc.home_city,
                device_id=switching_device,
                channel=Channel.ONLINE,
                card_present=False,
                transaction_type=TransactionType.PURCHASE,
                scenario_label="RAPID_DEVICE_SWITCH",
            )
            acc.recent_transactions.append(tx)
            transactions.append(tx)

        return transactions

    # -------------------------------------------------------------
    # Scenario 8: Mixed (Probabilistic Selection)
    # -------------------------------------------------------------
    def generate_mixed(
        self,
        scenario_weights: Optional[Dict[str, float]] = None,
        base_time: Optional[datetime] = None,
    ) -> List[Transaction]:
        """
        Samples a scenario based on configurable probabilities.
        Returns a list of 1 or more transactions (e.g. burst for velocity spike).
        """
        weights = scenario_weights or {
            "normal": 0.90,
            "high_amount": 0.03,
            "velocity_spike": 0.02,
            "new_device": 0.02,
            "unusual_merchant": 0.015,
            "unusual_location": 0.015,
        }

        scenarios = list(weights.keys())
        probabilities = list(weights.values())
        chosen = self.rng.choices(scenarios, weights=probabilities, k=1)[0]

        if chosen == "normal":
            return [self.generate_normal(base_time=base_time)]
        elif chosen == "high_amount":
            return [self.generate_high_amount(base_time=base_time)]
        elif chosen == "velocity_spike":
            return self.generate_velocity_spike(base_time=base_time)
        elif chosen == "new_device":
            return [self.generate_new_device(base_time=base_time)]
        elif chosen == "unusual_merchant":
            return [self.generate_unusual_merchant(base_time=base_time)]
        elif chosen == "unusual_location":
            return [self.generate_unusual_location(base_time=base_time)]
        elif chosen == "rapid_device_switching":
            return self.generate_rapid_device_switching(base_time=base_time)
        else:
            return [self.generate_normal(base_time=base_time)]
