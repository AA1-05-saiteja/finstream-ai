"""
FinStream AI - Real-Time Machine Learning Inference Engine
Loads Phase 6 model artifacts, performs feature-aligned inference for XGBoost & Isolation Forest,
computes hybrid risk scores, and attaches local SHAP explanations.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from xgboost import XGBClassifier

# Ensure project root is in sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import settings
from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS
from models.risk_scoring import (
    assign_risk_level,
    calculate_hybrid_risk_score,
    normalize_isolation_forest_score,
)
from models.shap_explainer import TransactionSHAPExplainer, create_shap_explainer
from producer.transaction_generator import TransactionGenerator
from streaming.feature_engineering import RealTimeFeatureEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("model_predict")


class ModelInferenceEngine:
    """
    Production-grade inference engine for FinStream AI.
    Loads serialized models and orchestrates dual-model scoring and SHAP explainability.
    """

    def __init__(
        self,
        artifacts_dir: str = "models/artifacts",
        enable_shap: bool = True,
    ):
        self.artifacts_dir = Path(artifacts_dir)
        self.enable_shap = enable_shap
        self.feature_columns: List[str] = []
        self.xgb_model: Optional[XGBClassifier] = None
        self.if_model: Optional[IsolationForest] = None
        self.shap_explainer: Optional[TransactionSHAPExplainer] = None

        self._load_artifacts()

    def _load_artifacts(self) -> None:
        """Loads model artifacts from disk with explicit validation."""
        xgb_path = self.artifacts_dir / "xgboost_model.joblib"
        if_path = self.artifacts_dir / "isolation_forest.joblib"
        feat_path = self.artifacts_dir / "feature_columns.json"

        # Validate existence of required files
        for p, desc in [(xgb_path, "XGBoost model"), (if_path, "Isolation Forest model"), (feat_path, "Feature columns")]:
            if not p.exists():
                raise FileNotFoundError(
                    f"Required artifact '{desc}' not found at {p}.\n"
                    f"Please run 'python -m models.train_all' to train and export Phase 6 artifacts."
                )

        logger.info("Loading model artifacts from %s...", self.artifacts_dir)
        with open(feat_path, "r") as f:
            self.feature_columns = json.load(f)

        self.xgb_model = joblib.load(xgb_path)
        self.if_model = joblib.load(if_path)

        if self.enable_shap:
            self.shap_explainer = create_shap_explainer(
                model=self.xgb_model,
                feature_names=self.feature_columns,
            )

        logger.info(
            "Inference engine initialized successfully. Feature count: %d, SHAP: %s",
            len(self.feature_columns),
            "Enabled" if self.enable_shap else "Disabled",
        )

    def prepare_feature_array(self, feature_record: Dict[str, Any]) -> np.ndarray:
        """
        Extracts and aligns features according to the exact training feature ordering.
        Missing features are safely imputed with 0.0.
        """
        row = []
        for col in self.feature_columns:
            val = feature_record.get(col, 0.0)
            try:
                row.append(float(val))
            except (ValueError, TypeError):
                row.append(0.0)
        return np.array([row], dtype=np.float64)

    def predict_single(
        self,
        transaction_dict: Dict[str, Any],
        explain: bool = False,
        top_n_shap: int = 5,
    ) -> Dict[str, Any]:
        """
        Runs dual-model inference on a single feature-enriched transaction.
        """
        if self.xgb_model is None or self.if_model is None:
            raise RuntimeError("Inference engine models are not loaded.")

        X = self.prepare_feature_array(transaction_dict)
        X_df = pd.DataFrame(X, columns=self.feature_columns)

        # 1. Supervised XGBoost Probability
        xgb_proba = float(self.xgb_model.predict_proba(X_df)[0, 1])

        # 2. Unsupervised Isolation Forest Score
        raw_if_score = float(-self.if_model.decision_function(X_df)[0])
        if_norm = normalize_isolation_forest_score(raw_if_score)

        # 3. Hybrid Risk Score & Categorical Level
        hybrid_score = calculate_hybrid_risk_score(
            xgboost_prob=xgb_proba,
            isolation_forest_norm=if_norm,
        )
        risk_level = assign_risk_level(hybrid_score)

        # 4. Extract transaction identifiers
        tx_id = str(transaction_dict.get("transaction_id", "UNKNOWN"))
        account_id = str(transaction_dict.get("account_id", "UNKNOWN"))
        amount = float(transaction_dict.get("amount", 0.0))

        result: Dict[str, Any] = {
            "transaction_id": tx_id,
            "account_id": account_id,
            "amount": round(amount, 2),
            "xgboost_probability": round(xgb_proba, 4),
            "isolation_forest_score": round(raw_if_score, 4),
            "isolation_forest_normalized": if_norm,
            "hybrid_risk_score": hybrid_score,
            "risk_level": risk_level,
        }

        # 5. Local SHAP Explanation
        if explain and self.shap_explainer:
            shap_top = self.shap_explainer.explain_transaction(
                features_dict_or_row=transaction_dict,
                top_n=top_n_shap,
            )
            result["top_shap_features"] = shap_top

        return result


_global_inference_engine: Optional[ModelInferenceEngine] = None


def load_inference_engine(artifacts_dir: str = "models/artifacts") -> ModelInferenceEngine:
    """Convenience factory returning a cached inference engine instance."""
    global _global_inference_engine
    if _global_inference_engine is None or _global_inference_engine.artifacts_dir != artifacts_dir:
        _global_inference_engine = ModelInferenceEngine(artifacts_dir=artifacts_dir)
    return _global_inference_engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FinStream AI Real-Time Inference & SHAP Explainability Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--rate", type=float, default=2.0, help="Transactions per second")
    parser.add_argument("--duration", type=float, default=5.0, help="Run duration in seconds")
    parser.add_argument("--scenario", type=str, default="mixed", help="Scenario pattern")
    parser.add_argument("--explain-all", action="store_true", help="Generate SHAP explanation for all records")
    parser.add_argument("--artifacts-dir", type=str, default="models/artifacts", help="Artifacts directory")
    return parser.parse_args()


def main():
    args = parse_args()
    engine = ModelInferenceEngine(artifacts_dir=args.artifacts_dir, enable_shap=True)
    feature_engine = RealTimeFeatureEngine()
    feature_engine.reset()

    generator = TransactionGenerator(
        rate=args.rate,
        scenario=args.scenario,
        seed=42,
    )

    logger.info(
        "Starting real-time ML inference & SHAP engine stream (Rate: %.1f TPS, Duration: %.1fs)...",
        args.rate,
        args.duration,
    )

    count = 0
    start_time = time.time()
    for tx in generator.stream_transactions(duration=args.duration):
        count += 1
        tx_dict = tx.model_dump()
        enriched = feature_engine.enrich_transaction(tx_dict)

        # Explain if high risk or requested
        is_high_risk = enriched.get("amount", 0) > 50000
        should_explain = args.explain_all or is_high_risk

        pred_result = engine.predict_single(enriched, explain=should_explain)
        print(json.dumps(pred_result, indent=2))

    elapsed = time.time() - start_time
    logger.info("Processed %d transactions through ML pipeline in %.2fs (%.2f TPS)", count, elapsed, count / elapsed)


if __name__ == "__main__":
    main()
