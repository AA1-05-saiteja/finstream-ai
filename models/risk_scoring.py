"""
FinStream AI - Hybrid Risk Scoring & Level Assignment Engine
Combines supervised XGBoost anomaly probabilities with unsupervised Isolation Forest scores
into a unified, calibrated risk index with categorical risk levels.
"""

from typing import Any, Dict, Optional
from config import settings


def normalize_isolation_forest_score(
    raw_score: float,
    min_bound: float = -0.15,
    max_bound: float = 0.25,
) -> float:
    """
    Normalizes inverted Isolation Forest anomaly score into [0.0, 1.0].
    Higher normalized score indicates stronger anomaly indication.
    
    Formula:
        normalized = (raw_score - min_bound) / (max_bound - min_bound), clipped to [0, 1]
    """
    if max_bound <= min_bound:
        raise ValueError("max_bound must be strictly greater than min_bound.")

    scaled = (float(raw_score) - min_bound) / (max_bound - min_bound)
    clamped = max(0.0, min(1.0, scaled))
    return round(clamped, 4)


def calculate_hybrid_risk_score(
    xgboost_prob: float,
    isolation_forest_norm: float,
    weight_xgb: float = 0.70,
    weight_if: float = 0.30,
) -> float:
    """
    Calculates weighted hybrid risk score from supervised and unsupervised predictions.
    
    Formula:
        Risk = (w_xgb * P_xgb) + (w_if * S_if_norm)
    """
    if not (0.0 <= xgboost_prob <= 1.0):
        raise ValueError(f"XGBoost probability must be in [0.0, 1.0], got {xgboost_prob}")

    if not (0.0 <= isolation_forest_norm <= 1.0):
        raise ValueError(f"Normalized Isolation Forest score must be in [0.0, 1.0], got {isolation_forest_norm}")

    if abs((weight_xgb + weight_if) - 1.0) > 1e-5:
        raise ValueError(f"Weights must sum to 1.0 (got {weight_xgb} + {weight_if} = {weight_xgb + weight_if})")

    hybrid_score = (weight_xgb * float(xgboost_prob)) + (weight_if * float(isolation_forest_norm))
    clamped_score = max(0.0, min(1.0, hybrid_score))
    return round(clamped_score, 4)


def assign_risk_level(
    risk_score: float,
    low_threshold: float = 0.30,
    high_threshold: float = 0.70,
) -> str:
    """
    Assigns qualitative risk category based on numerical risk score:
    - LOW: [0.00, low_threshold)
    - MEDIUM: [low_threshold, high_threshold)
    - HIGH: [high_threshold, 1.00]
    """
    if not (0.0 <= risk_score <= 1.0):
        raise ValueError(f"Risk score must be in [0.0, 1.0], got {risk_score}")

    if risk_score < low_threshold:
        return "LOW"
    elif risk_score < high_threshold:
        return "MEDIUM"
    else:
        return "HIGH"


def build_risk_assessment_record(
    transaction_id: str,
    account_id: str,
    amount: float,
    xgboost_prob: float,
    raw_if_score: float,
    weight_xgb: float = 0.70,
    weight_if: float = 0.30,
    low_threshold: Optional[float] = None,
    high_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Constructs a complete, validated risk assessment dictionary for a transaction.
    """
    thresh_low = low_threshold if low_threshold is not None else settings.RISK_THRESHOLD_LOW
    thresh_high = high_threshold if high_threshold is not None else settings.RISK_THRESHOLD_HIGH

    if_norm = normalize_isolation_forest_score(raw_if_score)
    hybrid_score = calculate_hybrid_risk_score(
        xgboost_prob=xgboost_prob,
        isolation_forest_norm=if_norm,
        weight_xgb=weight_xgb,
        weight_if=weight_if,
    )
    risk_level = assign_risk_level(
        risk_score=hybrid_score,
        low_threshold=thresh_low,
        high_threshold=thresh_high,
    )

    return {
        "transaction_id": transaction_id,
        "account_id": account_id,
        "amount": round(float(amount), 2),
        "xgboost_probability": round(float(xgboost_prob), 4),
        "isolation_forest_score": round(float(raw_if_score), 4),
        "isolation_forest_normalized": if_norm,
        "hybrid_risk_score": hybrid_score,
        "risk_level": risk_level,
    }
