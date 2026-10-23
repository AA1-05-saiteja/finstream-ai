# FinStream AI — Academic Presentation Slide Deck

---

## Slide 1: Title & Project Overview

### **FinStream AI: A Real-Time Financial Transaction Intelligence and Anomaly Detection Platform**
- **Author**: Data Science & Machine Learning Major Project
- **Domain**: Financial Technology (FinTech), Event-Driven Streaming & Explainable AI (XAI)
- **Key Proposition**: Dual-model risk scoring and real-time behavioral sliding windows combined with local SHAP feature attributions and zero-install interactive bank statement intelligence.
- **Academic Verification**: 113/113 automated unit & integration tests passing; sub-30ms inference latency; zero data leakage.

---

## Slide 2: Problem Statement & Motivation

### **Limitations of Traditional Financial Fraud Detection**
- **Rule-Based Systems**: Static `IF-ELSE` threshold checks create overwhelming false-positive rates (often >90%), fatiguing human risk investigators.
- **Batch Processing Lag**: T+1 or nightly batch processing flags fraudulent transactions hours or days after financial settlement has finalized.
- **Zero-Day & Velocity Blindspots**: Traditional rules cannot detect novel attack vectors (e.g., micro-probing before major off-hour transfers, sudden cross-city velocity spikes).
- **Black-Box AI Impasse**: Complex deep learning models output risk scores without explaining *why*, violating financial transparency regulations (e.g., RBI guidelines, GDPR Article 22).

---

## Slide 3: Proposed Solution

### **FinStream AI Architectural Philosophy**
1. **Event-Driven Streaming**: Real-time message ingestion via Apache Kafka with PySpark Structured Streaming.
2. **Behavioral Sliding Windows**: On-the-fly state calculation for 23 streaming features across 1-minute, 5-minute, and 1-hour event windows.
3. **Dual-Model Inference**:
   - Supervised **XGBoost Classifier** ($P_{\text{xgb}}$) to detect known fraud patterns.
   - Unsupervised **Isolation Forest** ($S_{\text{if\_norm}}$) to detect novel zero-day anomalies.
4. **Hybrid Risk Formulation**: Weighted ensemble ($0.70 \times P_{\text{xgb}} + 0.30 \times S_{\text{if\_norm}}$) producing calibrated risk tiers:
   - 🟢 `LOW` ($< 0.40$)
   - 🟡 `MEDIUM` ($0.40 - 0.69$)
   - 🔴 `HIGH` ($\ge 0.70$)
5. **Explainability by Design**: Real-time **SHAP TreeExplainer** outputting top-5 local attributions for every flagged transaction.
6. **Dual Ingestion Modalities**: Live streaming transactions and multi-format bank statement intelligence (CSV/XLSX).

---

## Slide 4: End-to-End System Architecture

```text
┌────────────────────────────────────────────────────────┐
│               Transaction Ingestion Sources            │
│  [ Synthetic Generator ]  [ Bank Statements (CSV/XLSX) ]│
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│           Message Streaming & Buffer Layer             │
│        Apache Kafka Broker (Topic: transactions)        │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│          Stream Processing & State Enrichment          │
│   PySpark 3.5.1 + 23-Feature Sliding Window Engine     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│           Dual Machine Learning Intelligence           │
│    XGBoost Classifier    +    Isolation Forest         │
│         (0.70 weight)    +         (0.30 weight)       │
│                            │                           │
│                            ▼                           │
│                SHAP TreeExplainer (Top-5)              │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Persistence & Low-Latency Caching          │
│       PostgreSQL (Durability) + Redis (Hot State)      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│               Serving & Real-Time Dashboard            │
│    FastAPI REST APIs & WebSocket (Port 8000)           │
│   [ Live Monitor ] [ /statement ] [ /insights ]        │
└────────────────────────────────────────────────────────┘
```

---

## Slide 5: Machine Learning Methodology

### **Dual-Model Complementary Strategy**

| Model | Paradigm | Purpose | Target / Metric |
| :--- | :--- | :--- | :--- |
| **XGBoost Classifier** | Supervised Gradient Boosted Trees | Detects known, learned fraud patterns (e.g. rapid card switches, high-amount off-hour transfers). | **ROC-AUC: 0.9676**<br>Precision: 0.9757<br>Recall: 0.7461 |
| **Isolation Forest** | Unsupervised Ensembles of Isolation Trees | Detects novel zero-day anomalies by isolating rare partition depths without requiring prior fraud labels. | **Contamination: 0.05**<br>Normalized Score: $[0.0, 1.0]$ |

- **Mathematical Hybrid Score**:
  $$\text{Score}_{\text{hybrid}} = 0.70 \cdot P_{\text{xgb}} + 0.30 \cdot S_{\text{if\_norm}}$$
- Ensures that zero-day attacks missed by XGBoost are still intercepted by Isolation Forest, while preventing excessive false positives.

---

## Slide 6: Real-Time Feature Engineering (23 Features)

FinStream AI derives 23 dynamic behavioral features per transaction without future data leakage:

1. **Transaction Core (2)**: `amount`, `log_amount`
2. **Velocity Windows (3)**: `transaction_count_1m`, `transaction_count_5m`, `transaction_count_1h`
3. **Spending Aggregations (5)**: `total_amount_5m`, `total_amount_1h`, `average_amount_5m`, `average_amount_1h`, `maximum_amount_1h`
4. **Behavioral Deviations (2)**: `amount_deviation_from_recent_avg`, `amount_ratio_to_recent_avg`
5. **Entity Frequency (4)**: `merchant_transaction_count_1h`, `device_transaction_count_1h`, `city_transaction_count_1h`, `channel_transaction_count_1h`
6. **Card & Diversity Counters (4)**: `unique_device_count_1h`, `unique_merchant_count_1h`, `unique_city_count_1h`, `unique_channel_count_1h`
7. **Identity Flags (3)**: `new_device_flag`, `new_city_flag`, `known_device_flag`

---

## Slide 7: Explainable AI with SHAP

### **Why Local Explainability Matters**
- **Regulatory Requirement**: Compliance with fair lending and banking transparency mandates.
- **Analyst Decision Acceleration**: Human risk analysts can inspect flagged transactions in seconds rather than digging through raw database logs.

### **SHAP Implementation Highlights**
- Uses **TreeExplainer** optimized for tree-based ensembles.
- Computes exact Shapley values reflecting marginal feature contributions:
  $$\phi_i = \sum_{S \subseteq F \setminus \{i\}} \frac{|S|!(|F| - |S| - 1)!}{|F|!} \left[ f(S \cup \{i\}) - f(S) \right]$$
- Provides directional classification: `increases_anomaly` (pushes score toward fraud) vs. `decreases_anomaly` (pushes score toward normal).
- Displays top-5 ranked features with natural-language explanation summaries.

---

## Slide 8: Bank Statement Intelligence Engine

### **Zero-Cloud, Privacy-First Statement Analysis**
- **Multi-Format Ingestion**: Ingests 30-day bank statements in structured `.csv` and `.xlsx` formats.
- **Fuzzy Column Detection**: Matches variable banking schemas (`Date`, `Txn Ref`, `Description`, `Debit`, `Credit`, `Balance`, `Category`, `Channel`).
- **Data Quality Audit**: Identifies dropped identical duplicates, currency symbol cleaning, and date normalization.
- **Privacy First**: Sensitive 12–16 digit account and card numbers are masked (`XXXX XXXX 4821`).
- **True ML Scoring**: Evaluates every parsed record sequentially through the 23-feature engine and dual ML models (no hardcoded fakes).
- **Comprehensive Reporting**: 9 financial & risk KPI cards, category breakdown, spending timeline, and multi-sheet Excel export.

---

## Slide 9: Live Stream Intelligence & Drift Monitoring

### **Real-Time Streaming Operations**
- **Live Mode Toggle**: Switch between `● LIVE MODE` (active 2.5s evaluation) and `○ PAUSED`.
- **Instant Anomaly Alert Banner**: Automatically triggers upon high-risk detection ($S_{\text{risk}} \ge 0.70$) with a one-click **"Investigate"** link to the transaction profile.
- **Contextual Baseline Comparison**:
  - Compares historical statement metrics against the live stream in real time.
  - Dynamically calculates Risk Score Drift ($\Delta \text{Risk}$) and Spending Deviation ($\Delta \text{Amount}\%$).
  - Evaluates system state: `Baseline Synchronized`, `Moderate Divergence`, or `Elevated Risk Drift`.
- **Transparent Data Tagging**: Explicit UI badges distinguish:
  - `UPLOADED BANK STATEMENT`
  - `SIMULATED TRANSACTIONS`
  - `LIVE TRANSACTION STREAM`

---

## Slide 10: Verified Benchmarks & Conclusion

### **Empirical Performance Benchmarks**

| Performance Metric | Measured Value | Standard / Target |
| :--- | :--- | :--- |
| **XGBoost ROC-AUC** | **0.9676** | $\ge 0.90$ (Industry Grade) |
| **Median Inference Latency** | **26.06 ms** | $< 50\text{ ms}$ (Real-Time Target) |
| **Single-Core Throughput** | **~33 TPS** | Scalable via Kafka Partitions |
| **Automated Test Suite** | **113 / 113 Passed (100%)** | 0 failures, 0 regressions |
| **Platform Footprint** | **Zero-Install Web UI** | No Node/npm, pure Python/FastAPI |

### **Summary**
FinStream AI successfully bridges the gap between high-throughput streaming data engineering, dual-model machine learning, and explainable human-in-the-loop financial risk analytics.
