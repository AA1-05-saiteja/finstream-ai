"""
FinStream AI - Account Profiles and Behavioral State Management
Maintains synthetic account characteristics and state for realistic transaction generation.
"""

import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from producer.transaction_models import Channel, MerchantCategory

INDIAN_CITIES = [
    "Hyderabad",
    "Bengaluru",
    "Chennai",
    "Mumbai",
    "Delhi",
    "Pune",
    "Kolkata",
    "Ahmedabad",
    "Jaipur",
    "Lucknow",
]

MERCHANTS_BY_CATEGORY: Dict[str, List[str]] = {
    MerchantCategory.GROCERIES.value: [f"MER_GROC_{i:03d}" for i in range(1, 21)],
    MerchantCategory.ELECTRONICS.value: [f"MER_ELEC_{i:03d}" for i in range(1, 16)],
    MerchantCategory.FASHION.value: [f"MER_FASH_{i:03d}" for i in range(1, 16)],
    MerchantCategory.DINING.value: [f"MER_DINE_{i:03d}" for i in range(1, 21)],
    MerchantCategory.TRAVEL.value: [f"MER_TRAV_{i:03d}" for i in range(1, 11)],
    MerchantCategory.ENTERTAINMENT.value: [f"MER_ENT_{i:03d}" for i in range(1, 11)],
    MerchantCategory.UTILITIES.value: [f"MER_UTIL_{i:03d}" for i in range(1, 11)],
    MerchantCategory.LUXURY.value: [f"MER_LUX_{i:03d}" for i in range(1, 11)],
    MerchantCategory.HEALTHCARE.value: [f"MER_HLTH_{i:03d}" for i in range(1, 11)],
}


@dataclass
class AccountProfile:
    """Represents the behavioral baseline of a single synthetic account."""
    account_id: str
    user_type: str  # 'NORMAL_USER' or 'HIGH_VALUE_USER'
    home_city: str
    known_devices: List[str]
    preferred_categories: List[str]
    avg_amount: float
    std_amount: float
    min_amount: float
    max_amount: float
    preferred_channels: List[Channel]
    last_transaction_time: Optional[datetime] = None
    transaction_count: int = 0
    recent_transactions: deque = field(default_factory=lambda: deque(maxlen=20))

    def get_preferred_device(self, rng: random.Random) -> str:
        """Returns one of the account's registered known devices."""
        return rng.choice(self.known_devices)

    def sample_normal_amount(self, rng: random.Random) -> float:
        """Samples a realistic amount using a Gaussian distribution clipped to min/max."""
        raw_val = rng.gauss(self.avg_amount, self.std_amount)
        # Add realistic cents variation
        amount = max(self.min_amount, min(self.max_amount, raw_val))
        return round(amount, 2)


class AccountPool:
    """Manages a collection of synthetic account profiles."""

    def __init__(self, size: int = 200, seed: Optional[int] = None):
        self.size = size
        self.rng = random.Random(seed)
        self.accounts: Dict[str, AccountProfile] = {}
        self._initialize_population()

    def _initialize_population(self) -> None:
        """Pre-populates realistic account profiles."""
        all_categories = [c.value for c in MerchantCategory]
        all_channels = [Channel.ONLINE, Channel.POS, Channel.MOBILE, Channel.ATM]

        for i in range(1, self.size + 1):
            account_id = f"ACC{i:04d}"
            is_high_value = self.rng.random() < 0.15
            user_type = "HIGH_VALUE_USER" if is_high_value else "NORMAL_USER"

            home_city = self.rng.choice(INDIAN_CITIES)
            num_devices = self.rng.choice([1, 1, 2, 2, 3])
            known_devices = [f"DEV{self.rng.randint(1000, 9999)}" for _ in range(num_devices)]

            if is_high_value:
                preferred_categories = self.rng.sample(
                    all_categories, k=self.rng.randint(4, 6)
                )
                avg_amount = self.rng.uniform(8000.0, 25000.0)
                std_amount = avg_amount * 0.35
                min_amount = 500.0
                max_amount = 75000.0
                preferred_channels = [Channel.ONLINE, Channel.POS, Channel.MOBILE]
            else:
                # Normal user
                normal_favs = [
                    MerchantCategory.GROCERIES.value,
                    MerchantCategory.DINING.value,
                    MerchantCategory.UTILITIES.value,
                    MerchantCategory.FASHION.value,
                ]
                preferred_categories = list(
                    set(self.rng.sample(normal_favs, k=3) + self.rng.sample(all_categories, k=1))
                )
                avg_amount = self.rng.uniform(300.0, 2200.0)
                std_amount = avg_amount * 0.40
                min_amount = 50.0
                max_amount = 8000.0
                preferred_channels = all_channels

            profile = AccountProfile(
                account_id=account_id,
                user_type=user_type,
                home_city=home_city,
                known_devices=known_devices,
                preferred_categories=preferred_categories,
                avg_amount=avg_amount,
                std_amount=std_amount,
                min_amount=min_amount,
                max_amount=max_amount,
                preferred_channels=preferred_channels,
            )
            self.accounts[account_id] = profile

    def get_account(self, account_id: str) -> AccountProfile:
        return self.accounts[account_id]

    def sample_account(self) -> AccountProfile:
        """Samples an account from the pool."""
        account_id = self.rng.choice(list(self.accounts.keys()))
        return self.accounts[account_id]

    def get_all_account_ids(self) -> List[str]:
        return list(self.accounts.keys())
