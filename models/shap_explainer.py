"""
FinStream AI - SHAP Explainability & Model Interpretation Module
Computes local feature importance attributions for XGBoost anomaly predictions
using SHAP TreeExplainer.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import shap
from xgboost import XGBClassifier

# Ensure project root is in sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("shap_explainer")


class TransactionSHAPExplainer:
    """
    Computes local feature importance attributions for XGBoost model predictions.
    Ranks features by absolute SHAP contribution and assigns directional tags.
    """

    def __init__(
        self,
        model: XGBClassifier,
        feature_names: Optional[List[str]] = None,
    ):
        self.model = model
        self.feature_names = feature_names or ALL_ENGINEERED_FEATURE_COLUMNS
        logger.info("Initializing SHAP TreeExplainer on XGBoost model...")
        self.explainer = shap.TreeExplainer(self.model)
        logger.info("SHAP TreeExplainer initialized successfully.")

    def explain_transaction(
        self,
        features_dict_or_row: Any,
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Calculates top-N SHAP feature contributions for a single transaction vector.
        
        Returns:
            List of dictionaries sorted by absolute SHAP value descending:
            [
                {
                    "feature": "amount",
                    "feature_value": 85000.0,
                    "shap_value": 1.42,
                    "absolute_shap_value": 1.42,
                    "direction": "increases_anomaly"
                },
                ...
            ]
        """
        # Convert input to 2D numpy array or DataFrame aligned to feature_names
        if isinstance(features_dict_or_row, dict):
            row_values = [float(features_dict_or_row.get(col, 0.0)) for col in self.feature_names]
            X = np.array([row_values], dtype=np.float64)
        elif isinstance(features_dict_or_row, pd.DataFrame):
            X = features_dict_or_row[self.feature_names].values
        elif isinstance(features_dict_or_row, pd.Series):
            X = np.array([[float(features_dict_or_row.get(col, 0.0)) for col in self.feature_names]], dtype=np.float64)
        elif isinstance(features_dict_or_row, np.ndarray):
            X = features_dict_or_row if features_dict_or_row.ndim == 2 else np.array([features_dict_or_row])
        else:
            raise TypeError(f"Unsupported features type: {type(features_dict_or_row)}")

        # Calculate SHAP values (raw margin log-odds or probabilities)
        shap_values = self.explainer.shap_values(X)
        if isinstance(shap_values, list):
            # Binary classification list [class 0, class 1]
            raw_shap = shap_values[1][0]
        elif shap_values.ndim == 2:
            raw_shap = shap_values[0]
        else:
            raw_shap = shap_values

        contributions: List[Dict[str, Any]] = []
        for i, feature_name in enumerate(self.feature_names):
            s_val = float(raw_shap[i])
            f_val = float(X[0, i])
            abs_s = abs(s_val)

            if s_val > 1e-4:
                direction = "increases_anomaly"
            elif s_val < -1e-4:
                direction = "decreases_anomaly"
            else:
                direction = "neutral"

            contributions.append({
                "feature": feature_name,
                "feature_value": round(f_val, 4),
                "shap_value": round(s_val, 4),
                "absolute_shap_value": round(abs_s, 4),
                "direction": direction,
            })

        # Sort by absolute SHAP contribution descending
        contributions.sort(key=lambda item: item["absolute_shap_value"], reverse=True)
        return contributions[:top_n]


def create_shap_explainer(
    model: XGBClassifier,
    feature_names: Optional[List[str]] = None,
) -> TransactionSHAPExplainer:
    """Factory helper to instantiate a TransactionSHAPExplainer."""
    return TransactionSHAPExplainer(model=model, feature_names=feature_names)
