# Phase 6 — Machine Learning Model Training & Evaluation

This document details the offline machine learning architecture, training methodology, synthetic ground-truth labeling, feature matrices, and evaluation metrics for **FinStream AI**.

## 1. Architecture Flow

```mermaid
flowchart TD
    A[Synthetic Transaction Data\n(models/training_data.py)] --> B[Feature Extraction & Leakage Prevention\n(23 Numeric Engineered Features)]
    B --> C[Stratified Train/Test Split\n(80% Train / 20% Test)]

    C --> D[Supervised XGBoost Classifier\n(models/train_xgboost.py)]
    C --> E[Unsupervised Isolation Forest\n(models/train_isolation_forest.py)]

    D --> F[XGBoost Evaluation\n(Precision, Recall, F1, ROC/PR-AUC)]
    E --> G[Isolation Forest Benchmark\n(Inverted Anomaly Score)]

    F --> H[Evaluation Reports\nreports/phase6_evaluation.md]
    G --> H

    D --> I[XGBoost Artifacts\nmodels/artifacts/xgboost_model.joblib]
    E --> J[Isolation Forest Artifacts\nmodels/artifacts/isolation_forest.joblib]
```

## 2. Synthetic Ground-Truth Labeling Strategy

In financial transaction intelligence, supervised training requires high-quality ground-truth labels. In FinStream AI, synthetic ground truth is defined as:
* **`y = 0` (Normal baseline)**: Regular transactions reflecting typical account amount distributions, home cities, registered devices, and standard categories.
* **`y = 1` (Synthetic anomalies)**: Injected scenario variations:
  - `HIGH_AMOUNT`: 12x–35x spending spikes exceeding historical maximums.
  - `VELOCITY_SPIKE`: 3–6 rapid transactions within 1-minute event-time windows.
  - `NEW_DEVICE`: Unseen device IDs not registered in account baseline.
  - `UNUSUAL_MERCHANT`: Uncharacteristic merchant verticals.
  - `UNUSUAL_LOCATION`: Geographical displacements to distant cities.
  - `RAPID_DEVICE_SWITCH`: Rapid cycling of devices in succession.

## 3. Prevention of Target Leakage

To ensure model generalizability:
1. All identifiers (`transaction_id`, `account_id`, `merchant_id`, `device_id`, `timestamp`) are dropped before model training.
2. The scenario flag (`scenario_label`) and target variable (`is_anomaly`) are strictly excluded from the feature matrix $X$.
3. The model trains purely on the 23 behavioral, velocity, spending deviation, and cardinality signals created in Phase 5.

## 4. Models Overview

### Supervised XGBoost
* **Objective**: `binary:logistic` predicting $P(\text{anomaly} \mid X)$.
* **Key Hyperparameters**: `n_estimators=100`, `max_depth=5`, `learning_rate=0.08`, `subsample=0.8`, `colsample_bytree=0.8`.
* **Classification Threshold**: Default `0.50`.

### Unsupervised Isolation Forest
* **Objective**: Isolates anomalies in tree partitions without utilizing ground-truth labels during fitting.
* **Score Inversion**: Scikit-Learn's `decision_function` is inverted ($\text{score} = -\text{decision\_function}(X)$) so that higher values consistently represent greater anomaly likelihood.
* **Contamination**: Set to `0.10` for development benchmarking.

## 5. Measured Model Evaluation Metrics (Test Set, N=2,000)

| Metric | Supervised XGBoost | Unsupervised Isolation Forest |
| :--- | :---: | :---: |
| **Accuracy** | 0.9560 | 0.8080 |
| **Precision** | 0.9757 | 0.3512 |
| **Recall** | 0.7461 | 0.2229 |
| **F1-Score** | 0.8456 | 0.2727 |
| **ROC-AUC** | 0.9676 | 0.7348 |
| **PR-AUC** | 0.9210 | 0.3207 |

## 6. Execution Commands

```powershell
# 1. Generate synthetic training dataset
python -m models.training_data --samples 10000 --seed 42

# 2. Train and evaluate XGBoost
python -m models.train_xgboost --samples 10000 --seed 42

# 3. Train and evaluate Isolation Forest
python -m models.train_isolation_forest --samples 10000 --seed 42

# 4. Or execute full pipeline and generate reports
python -m models.train_all --samples 10000 --seed 42
```
