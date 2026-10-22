"""
FinStream AI - Transaction Models and Validation Schemas
Defines strongly-typed Pydantic schemas and enums for synthetic transactions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Channel(str, Enum):
    ONLINE = "ONLINE"
    POS = "POS"
    ATM = "ATM"
    MOBILE = "MOBILE"


class TransactionType(str, Enum):
    PURCHASE = "PURCHASE"
    TRANSFER = "TRANSFER"
    WITHDRAWAL = "WITHDRAWAL"
    PAYMENT = "PAYMENT"


class MerchantCategory(str, Enum):
    GROCERIES = "groceries"
    ELECTRONICS = "electronics"
    FASHION = "fashion"
    DINING = "dining"
    TRAVEL = "travel"
    ENTERTAINMENT = "entertainment"
    UTILITIES = "utilities"
    LUXURY = "luxury"
    HEALTHCARE = "healthcare"


class Transaction(BaseModel):
    """
    Strongly-typed synthetic transaction model.
    Validates data integrity and enforces positive amounts and realistic constraints.
    """
    transaction_id: str = Field(..., min_length=3, description="Unique transaction identifier")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    account_id: str = Field(..., min_length=3, description="Synthetic account identifier")
    amount: float = Field(..., gt=0.0, description="Transaction amount in INR")
    currency: str = Field(default="INR", description="Currency code (Default: INR)")
    merchant_id: str = Field(..., min_length=3, description="Synthetic merchant identifier")
    merchant_category: str = Field(..., description="Category of merchant")
    city: str = Field(..., min_length=2, description="City where transaction originated")
    device_id: str = Field(..., min_length=3, description="Device identifier")
    channel: Channel = Field(..., description="Transaction channel")
    card_present: bool = Field(default=False, description="Whether physical card was present")
    transaction_type: TransactionType = Field(
        default=TransactionType.PURCHASE, description="Type of transaction"
    )
    scenario_label: Optional[str] = Field(
        default=None, description="Internal synthetic scenario tag (for evaluation/debugging)"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be strictly positive (> 0)")
        return round(float(v), 2)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v_upper = v.upper().strip()
        if v_upper != "INR":
            raise ValueError(f"Unsupported currency '{v}'. Only 'INR' is supported in prototype.")
        return v_upper

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        try:
            # Verify string parses as ISO datetime
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(f"Invalid ISO 8601 timestamp string: {v}") from e
        return v

    def to_clean_dict(self, include_scenario: bool = False) -> dict:
        """Export transaction as dictionary matching public contract."""
        data = self.model_dump()
        if not include_scenario:
            data.pop("scenario_label", None)
        return data
