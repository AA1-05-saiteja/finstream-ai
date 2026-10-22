# FinStream AI — Phase 6 Model Training & Evaluation Report

**Generated At (UTC)**: 2026-10-01T13:33:58.920556+00:00  
**Random Seed**: 42  
**Evaluation Scope**: Offline Academic Benchmark against Synthetic Ground Truth  

---

## 1. Dataset & Ground-Truth Methodology

* **Total Records**: 10,000
* **Feature Count**: 23
* **Normal Records (y=0)**: 8,385 (83.85%)
* **Synthetic Anomalies (y=1)**: 1,615 (16.15%)
* **Train / Test Split**: 8,000 train / 2,000 test (80/20 Stratified)

### Labeling Strategy
Labels are assigned deterministically based on synthetic scenario patterns:
* `y = 0` (Normal baseline): Gaussian spending around account mean, preferred merchants, known devices, home city.
* `y = 1` (Synthetic anomalies): High-amount spikes (> ₹65,000), 1-minute velocity bursts, unseen devices, merchant shifts, and distant city displacements.

*Target Leakage Prevention*: Identifiers (`transaction_id`, `account_id`, `merchant_id`, `device_id`, `city`, `timestamp`) and scenario tags (`scenario_label`) were strictly excluded from feature matrix $X$.

---

## 2. Model Performance Comparison

| Evaluation Metric | Supervised XGBoost | Unsupervised Isolation Forest |
| :--- | :---: | :---: |
| **Accuracy** | 0.9560 | 0.8080 |
| **Precision** | 0.9757 | 0.3512 |
| **Recall** | 0.7461 | 0.2229 |
| **F1-Score** | 0.8456 | 0.2727 |
| **ROC-AUC** | 0.9676 | 0.7348 |
| **PR-AUC** | 0.9210 | 0.3207 |

---

## 3. Supervised Model: XGBoost Classifier

### Hyperparameters
```json
{
  "n_estimators": 100,
  "max_depth": 5,
  "learning_rate": 0.08,
  "subsample": 0.8,
  "colsample_bytree": 0.8,
  "random_state": 42,
  "eval_metric": "logloss",
  "n_jobs": -1
}
```

### Confusion Matrix (Test Set, N=2,000)
* **True Negatives (TN)**: 1671
* **False Positives (FP)**: 6
* **False Negatives (FN)**: 82
* **True Positives (TP)**: 241

---

## 4. Unsupervised Model: Isolation Forest

### Hyperparameters
```json
{
  "n_estimators": 100,
  "contamination": 0.1,
  "max_samples": "auto",
  "random_state": 42,
  "n_jobs": -1
}
```

### Anomaly Score Interpretation
* Scikit-Learn's raw `decision_function` outputs negative values for outliers and positive for inliers.
* For consistent benchmark alignment, scores are inverted ($\text{anomaly\_score} = -\text{decision\_function}(X)$), so higher values represent stronger anomaly likelihood.

### Confusion Matrix (Test Set, N=2,000)
* **True Negatives (TN)**: 1544
* **False Positives (FP)**: 133
* **False Negatives (FN)**: 251
* **True Positives (TP)**: 72

---

## 5. Limitations & Academic Disclaimer

1. **Synthetic Ground Truth**: The models were trained and benchmarked strictly on synthetically generated transactions and scenario distributions. Performance figures reflect pattern separation in synthetic data rather than real banking environments.
2. **Offline Evaluation**: Metrics are measured on held-out test splits without streaming latency or database write contention.
3. **No Automated Blocking**: FinStream AI is designed as a decision-support system to flag anomalous patterns for human analyst review.
