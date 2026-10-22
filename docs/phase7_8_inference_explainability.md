# Phase 7 & 8 — Real-Time ML Inference, Hybrid Risk Scoring & SHAP Explainability

This document details the real-time inference engine, dual-model hybrid risk scoring mechanism, and SHAP explainability layer for **FinStream AI**.

## 1. Architecture Flow

```mermaid
flowchart TD
    A[Feature-Enriched Transaction Stream\n(Phase 5 Features)] --> B[Inference Engine\n(models/predict.py)]

    subgraph Dual Model Scoring
        B --> C[Supervised XGBoost Classifier\n(models/artifacts/xgboost_model.joblib)]
        B --> D[Unsupervised Isolation Forest\n(models/artifacts/isolation_forest.joblib)]

        C --> E[XGBoost Probability\nP_xgb in 0.0 - 1.0]
        D --> F[Raw IF Decision Score\n-decision_function(X)]
        F --> G[Min-Max Normalization\nS_if_norm in 0.0 - 1.0]
    end

    E --> H[Hybrid Risk Scoring Engine\n(models/risk_scoring.py)]
    G --> H

    H --> I[Weighted Formula\n0.70 * P_xgb + 0.30 * S_if_norm]
    I --> J[Categorical Risk Level Assignment\nLOW < 0.30 | MEDIUM 0.30-0.70 | HIGH >= 0.70]

    subgraph Explainability Layer
        J --> K[Conditional SHAP Trigger\nExplain on Demand / High Risk]
        K --> L[SHAP TreeExplainer\n(models/shap_explainer.py)]
        L --> M[Top-5 Feature Contributions\nDirection: increases / decreases anomaly]
    end

    J --> N[Scored & Explained Output Payload\n(Ready for Phase 9/10 Storage & API)]
    M --> N
```

## 2. Hybrid Risk Scoring Methodology

FinStream AI combines supervised and unsupervised paradigms to deliver a robust anomaly score:

1. **Supervised XGBoost Probability ($P_{\text{xgb}} \in [0.0, 1.0]$)**:
   Predicts the likelihood that a transaction matches known synthetic anomaly patterns (velocity bursts, spending spikes, new devices, location leaps).

2. **Unsupervised Isolation Forest Score ($S_{\text{if\_norm}} \in [0.0, 1.0]$)**:
   Measures feature space isolation distance, detecting zero-day or unfamiliar behavioral shifts without relying on labeled targets:
   $$\text{raw\_if\_score} = -\text{decision\_function}(X)$$
   $$S_{\text{if\_norm}} = \text{clip}\left(\frac{\text{raw\_if\_score} - \text{min\_val}}{\text{max\_val} - \text{min\_val}}, 0.0, 1.0\right)$$
   *(with empirical reference range $[-0.20, 0.25]$)*

3. **Hybrid Risk Score Formula**:
   $$\text{Hybrid Risk Score} = (w_{\text{xgb}} \times P_{\text{xgb}}) + (w_{\text{if}} \times S_{\text{if\_norm}})$$
   * Default weights: $w_{\text{xgb}} = 0.70$, $w_{\text{if}} = 0.30$
   * Constraint: $w_{\text{xgb}} + w_{\text{if}} = 1.0$

4. **Risk Level Mapping**:
   * **`LOW`**: $\text{Score} < 0.30$
   * **`MEDIUM`**: $0.30 \le \text{Score} < 0.70$
   * **`HIGH`**: $\text{Score} \ge 0.70$

## 3. SHAP Local Explainability Layer

To satisfy financial model explainability standards (fairness, auditability, and investigator decision support):
* FinStream AI attaches a `shap.TreeExplainer` directly to the trained XGBoost model.
* For scored transactions, it extracts the local SHAP values for all 23 input features.
* The explainer ranks features by **absolute SHAP contribution** and returns the top-$N$ factors (default $N=5$).
* Each factor is classified with an intuitive directional label:
  - `increases_anomaly`: $\text{shap\_value} > 0.001$ (pushes risk score higher)
  - `decreases_anomaly`: $\text{shap\_value} < -0.001$ (pushes risk score lower)
  - `neutral`: $|\text{shap\_value}| \le 0.001$

## 4. Real-Time Inference Output Schema

```json
{
  "transaction_id": "TX000004",
  "account_id": "ACC0147",
  "amount": 350073.73,
  "xgboost_probability": 0.7948,
  "isolation_forest_score": 0.1848,
  "isolation_forest_normalized": 0.837,
  "hybrid_risk_score": 0.8074,
  "risk_level": "HIGH",
  "top_shap_features": [
    {
      "feature": "amount",
      "feature_value": 350073.73,
      "shap_value": 0.9912,
      "absolute_shap_value": 0.9912,
      "direction": "increases_anomaly"
    },
    {
      "feature": "city_transaction_count_1h",
      "feature_value": 1.0,
      "shap_value": 0.9415,
      "absolute_shap_value": 0.9415,
      "direction": "increases_anomaly"
    },
    {
      "feature": "device_transaction_count_1h",
      "feature_value": 1.0,
      "shap_value": 0.8113,
      "absolute_shap_value": 0.8113,
      "direction": "increases_anomaly"
    },
    {
      "feature": "maximum_amount_1h",
      "feature_value": 350073.73,
      "shap_value": 0.7944,
      "absolute_shap_value": 0.7944,
      "direction": "increases_anomaly"
    },
    {
      "feature": "channel_transaction_count_1h",
      "feature_value": 1.0,
      "shap_value": -0.7047,
      "absolute_shap_value": 0.7047,
      "direction": "decreases_anomaly"
    }
  ]
}
```

## 5. Verification Command

```powershell
# Run ML Inference demo with SHAP explanations
python -m models.predict --rate 2 --duration 5 --scenario mixed --explain
```
