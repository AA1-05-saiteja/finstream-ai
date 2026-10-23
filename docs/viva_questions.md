# FinStream AI — Comprehensive Viva Voce Examination Guide

This document contains 24 core technical questions and exhaustive answers covering architecture, machine learning, streaming data engineering, system design, and security.

---

### Q1: Why did you choose XGBoost for the supervised fraud detection model?
**Answer**:
XGBoost (Extreme Gradient Boosting) was chosen because:
1. **Tabular Performance**: Gradient-boosted decision trees consistently outperform deep learning networks on structured, heterogeneous tabular financial data with non-linear feature relationships.
2. **Inference Latency**: XGBoost generates optimized C++ tree evaluation structures capable of sub-millisecond per-sample prediction, critical for meeting our $< 50\text{ ms}$ latency budget.
3. **Handling Imbalance & Missingness**: XGBoost natively handles sparsity and offers hyperparameter controls like `scale_pos_weight` to address extreme class imbalance typical of financial fraud.
4. **Interpretability**: Enables direct integration with SHAP `TreeExplainer` for exact polynomial-time Shapley feature attribution.

---

### Q2: Why did you choose Isolation Forest for unsupervised anomaly detection?
**Answer**:
Isolation Forest operates on the principle that anomalies are "few and different". Instead of profiling normal data points via computationally expensive distance or density metrics (like k-NN or Local Outlier Factor), Isolation Forest recursively partitions feature space using random orthogonal splits. 
Because anomalous data points reside in sparse regions, they require significantly fewer splits to isolate (shorter average tree path length $h(x)$). It provides $O(n \log n)$ time complexity and minimal memory footprint, making it ideal for streaming data.

---

### Q3: Why combine two models (Dual-Model Ensemble) instead of relying solely on one?
**Answer**:
A single model paradigm exhibits inherent vulnerabilities:
- **Supervised models (XGBoost)** excel at identifying known, historical fraud vectors that existed in the training dataset, but suffer from blindspots when exposed to novel "zero-day" fraud attacks.
- **Unsupervised models (Isolation Forest)** excel at identifying statistical anomalies and novel deviations, but can produce false positives on legitimate high-value transactions (e.g., annual property taxes or festival purchases).

By blending them mathematically:
$$\text{Score}_{\text{hybrid}} = 0.70 \cdot P_{\text{xgb}} + 0.30 \cdot S_{\text{if\_norm}}$$
the system retains high precision against known attack patterns while providing a resilient safety net for zero-day behavioral deviations.

---

### Q4: What is the fundamental difference between supervised learning and anomaly detection?
**Answer**:
- **Supervised Learning**: Requires labeled training pairs $(X, y)$ where ground truth fraud labels ($y \in \{0, 1\}$) are explicitly known. The model optimizes a objective function (e.g., binary cross-entropy log-loss) to minimize classification error on known categories.
- **Anomaly Detection (Unsupervised)**: Operates strictly on unlabeled features $X$ without prior knowledge of class outcomes. It learns the expected geometric or statistical distribution of the baseline data and flags points that deviate significantly from that distribution.

---

### Q5: What is Explainable AI (XAI) and why is SHAP essential in FinStream AI?
**Answer**:
SHAP (SHapley Additive exPlanations) is rooted in cooperative game theory. It calculates the fair marginal contribution of each feature to the difference between the model's prediction and the base expected value. 
In banking and financial intelligence:
1. **Regulatory Compliance**: Financial regulations (RBI guidelines, EU GDPR Article 22, US Fair Credit Reporting Act) mandate the "right to explanation" when automated algorithms flag, freeze, or decline consumer accounts.
2. **Actionable Analyst Support**: Risk analysts cannot investigate hundreds of raw numeric features without context. SHAP highlights the top-5 influential factors (e.g., "Transaction velocity in 1h is 8x normal", "New device login") and shows their positive or negative directionality.

---

### Q6: What are the 23 engineered features and how are they structured?
**Answer**:
The 23 features capture multi-scale behavioral velocity, spending deviation, and entity diversity:
1. `amount`: Raw monetary transaction value.
2. `log_amount`: Logarithmic transformation $\ln(\text{amount} + 1)$ to normalize heavy right-skewed distributions.
3. `transaction_count_1m`: Number of transactions initiated by the account within the trailing 1-minute window.
4. `transaction_count_5m`: Number of transactions initiated within trailing 5 minutes.
5. `transaction_count_1h`: Number of transactions initiated within trailing 1 hour.
6. `total_amount_5m`: Cumulative spending in trailing 5 minutes.
7. `total_amount_1h`: Cumulative spending in trailing 1 hour.
8. `average_amount_5m`: Rolling average transaction size over trailing 5 minutes.
9. `average_amount_1h`: Rolling average transaction size over trailing 1 hour.
10. `maximum_amount_1h`: Peak single transaction amount observed in trailing 1 hour.
11. `minimum_amount_1h`: Lowest transaction amount observed in trailing 1 hour.
12. `amount_deviation_from_recent_avg`: Absolute deviation $|\text{amount} - \text{average\_amount\_1h}|$.
13. `amount_ratio_to_recent_avg`: Relative ratio $\frac{\text{amount}}{\text{average\_amount\_1h} + \epsilon}$.
14. `merchant_transaction_count_1h`: Frequency of transactions with this specific merchant in the past hour.
15. `device_transaction_count_1h`: Frequency of transactions from this specific hardware device ID in the past hour.
16. `city_transaction_count_1h`: Frequency of transactions from this geographic city in the past hour.
17. `channel_transaction_count_1h`: Frequency of transactions through this payment rail (UPI, POS, ATM, NetBanking).
18. `unique_device_count_1h`: Count of distinct physical devices utilized by the account in the past hour.
19. `unique_merchant_count_1h`: Count of distinct merchants transacted with in the past hour.
20. `unique_city_count_1h`: Count of distinct cities transacted from in the past hour (detects impossible geo-velocity).
21. `unique_channel_count_1h`: Count of distinct payment channels accessed in the past hour.
22. `new_device_flag`: Binary indicator (1 if device ID has not been previously registered for this account, else 0).
23. `new_city_flag`: Binary indicator (1 if geographic city differs from recent history, else 0).

---

### Q7: How is the final hybrid risk score calculated and calibrated?
**Answer**:
1. **XGBoost Output**: The model outputs calibrated fraud probability $P_{\text{xgb}} \in [0.0, 1.0]$.
2. **Isolation Forest Output**: Scikit-learn's `decision_function` outputs a raw anomaly score where negative numbers denote anomalies. We apply linear min-max normalization against empirical calibration bounds $[-0.30, 0.20]$:
   $$S_{\text{if\_norm}} = \text{clip}\left(\frac{0.20 - \text{score}_{\text{raw}}}{0.20 - (-0.30)}, 0.0, 1.0\right)$$
3. **Linear Combination**:
   $$\text{Score}_{\text{hybrid}} = 0.70 \cdot P_{\text{xgb}} + 0.30 \cdot S_{\text{if\_norm}}$$
4. **Risk Tier Assignment**:
   - $\text{Score}_{\text{hybrid}} < 0.40 \implies \mathbf{LOW}$
   - $0.40 \le \text{Score}_{\text{hybrid}} < 0.70 \implies \mathbf{MEDIUM}$
   - $\text{Score}_{\text{hybrid}} \ge 0.70 \implies \mathbf{HIGH}$

---

### Q8: How does real-time streaming feature calculation prevent target leakage?
**Answer**:
Target leakage occurs when future information or post-transaction data informs the features of an event. In FinStream AI:
1. Features are strictly computed using **event-time sliding windows** looking backward from timestamp $t_i$.
2. State update ordering guarantees that the rolling window evaluates historical transactions $(t < t_i)$ prior to updating the state with the current event $t_i$.
3. Time windows automatically evict transactions older than 1 hour, maintaining $O(1)$ memory bounds per account.

---

### Q9: What is WebSocket and why is it preferred over HTTP polling for live financial monitoring?
**Answer**:
HTTP polling requires the browser client to repeatedly send request headers every few seconds (polling overhead, TCP handshake latency, wasted bandwidth). 
WebSocket initiates a single HTTP handshake and upgrades to a full-duplex, persistent TCP connection. This allows the FastAPI server to push newly evaluated transactions and high-risk alerts to the dashboard immediately upon scoring with sub-millisecond network transit latency.

---

### Q10: Why choose FastAPI over Flask or Django?
**Answer**:
1. **Asynchronous Architecture (`async`/`await`)**: Built on Starlette and ASGI, enabling high concurrent request handling without blocking the worker thread during database I/O or model execution.
2. **Automatic Schema Validation**: Deep integration with Pydantic v2 enforces strict typed data contracts and automatic request validation.
3. **Interactive OpenAPI / Swagger**: Automatically generates live interactive documentation at `/docs` directly from code type hints.
4. **Performance**: Demonstrates near NodeJS/Go throughput benchmarks.

---

### Q11: What is Apache Kafka's architectural role in FinStream AI?
**Answer**:
Kafka acts as the distributed, fault-tolerant message streaming backbone:
1. **Decoupling**: Decouples high-volume transaction generation from downstream ML inference and database writes.
2. **Backpressure Buffering**: If ML inference or database indexing experiences temporary latency spikes, Kafka's partitioned log buffers inbound transactions without dropping messages.
3. **Partitioning & Ordering**: Keying messages by `account_id` guarantees strict chronological partition ordering per customer.

---

### Q12: Why use PySpark Structured Streaming?
**Answer**:
PySpark Structured Streaming provides:
1. **Event-Time Processing**: Accommodates out-of-order or late-arriving events using configurable watermarking thresholds (e.g., 5-minute watermarks).
2. **Fault Tolerance**: Utilizes distributed checkpointing and write-ahead logs (WAL) to guarantee **exactly-once** processing semantics.
3. **Scalability**: Can scale computation horizontally across multi-node clusters as transaction volumes expand.

---

### Q13: What role do PostgreSQL and Redis play together in the persistence layer?
**Answer**:
They form a complementary multi-tier persistence architecture:
- **PostgreSQL**: Serves as the relational System of Record (SoR) ensuring ACID durability across normalized tables (`transactions`, `risk_assessments`, `shap_explanations`).
- **Redis**: Serves as an in-memory cache providing sub-millisecond retrieval of hot account states, latest risk levels, and rate-limiting counters (`finstream:risk:*`, `finstream:account:*`).

---

### Q14: How does the Bank Statement Analyzer handle heterogeneous column headers?
**Answer**:
Different financial institutions export statements using inconsistent naming conventions (e.g., HDFC uses `Chq/Ref No`, SBI uses `Txn Ref`, ICICI uses `Reference No`). 
The `BankStatementAnalyzer` implements heuristic regex pattern matching across semantic roles (`date`, `id`, `description`, `debit`, `credit`, `amount`, `balance`, `category`, `channel`). It converts headers into lowercase alphanumeric slugs and assigns semantic mapping dynamically.

---

### Q15: How does the statement parser resolve debit/credit directions when only a single 'Amount' column is present?
**Answer**:
If separate `Debit` and `Credit` columns are present, direction is determined by which column contains a positive numeric value. 
If only a single `Amount` column exists:
1. The engine checks the mathematical sign (negative values indicate withdrawals/debits).
2. If positive, it inspects transaction narrations and auxiliary fields for keywords such as `"CR"`, `"DEPOSIT"`, `"SALARY"` vs. `"DR"`, `"WITHDRAWAL"`, `"PURCHASE"`.

---

### Q16: How are duplicate rows identified and handled during statement ingestion?
**Answer**:
Identical consecutive rows can occur when users re-export statements or upload duplicate files. 
FinStream AI runs multi-column deduplication matching on `(date, transaction_id, amount, description)`. Identical duplicate rows are safely discarded, and the exact count of removed duplicates is logged in the **Data Quality Audit** card.

---

### Q17: What security and privacy measures protect uploaded bank statements?
**Answer**:
1. **Zero External Cloud Egress**: Bank statements are processed entirely within the local FastAPI memory pipeline and are never transmitted to third-party APIs.
2. **PII Masking**: Regular expressions automatically detect 12-to-16 digit bank account and credit card numbers, masking all but the last 4 digits (e.g., `XXXX XXXX 4821`).
3. **Temporary File Ephemerality**: Uploaded byte buffers are processed in-memory and discarded upon completion.

---

### Q18: What is ROC-AUC and what does the measured score of 0.9676 signify?
**Answer**:
ROC-AUC (Receiver Operating Characteristic — Area Under Curve) evaluates the classifier's ability to discriminate between positive (fraud) and negative (legitimate) transactions across all possible classification probability thresholds. 
A score of **0.9676** indicates that given a randomly chosen fraudulent transaction and a randomly chosen legitimate transaction, the model ranks the fraudulent transaction higher **96.76%** of the time.

---

### Q19: What is the difference between latency and throughput in FinStream AI?
**Answer**:
- **Inference Latency**: The turnaround duration required to compute 23 features, execute dual-model inference, and derive SHAP attributions for a single transaction. FinStream AI achieves a **median latency of 26.06 ms**.
- **System Throughput**: The total number of transactions the pipeline can ingest, evaluate, and persist per unit time. Single-core local throughput benchmarks reach **~33 Transactions Per Second (TPS)**.

---

### Q20: How does the system prevent confusing simulated demo data with real bank statements?
**Answer**:
Every transaction record carries an explicit provenance tag in its schema:
- `UPLOADED BANK STATEMENT`: Transactions parsed from user-provided CSV/XLSX files.
- `SIMULATED TRANSACTIONS`: Transactions generated via preset scenario controls (e.g., High Amount, Rapid Velocity).
- `LIVE TRANSACTION STREAM`: Continuous live stream events delivered via the streaming runner.
The UI renders distinct badges for each data source to guarantee complete analytical transparency.

---

### Q21: What is the Contextual Baseline Comparison and how is Risk Drift calculated?
**Answer**:
When a bank statement is uploaded, it establishes a 30-day historical spending and risk baseline (Average Amount $\mu_{\text{stmt}}$, Average Risk $\bar{R}_{\text{stmt}}$). 
As live transactions arrive, the system computes:
$$\Delta \text{Risk} = \bar{R}_{\text{live}} - \bar{R}_{\text{stmt}}$$
$$\Delta \text{Amount}\% = \frac{\bar{A}_{\text{live}} - \mu_{\text{stmt}}}{\mu_{\text{stmt}}} \times 100$$
Based on these variances, the system categorizes behavioral drift as:
- **Baseline Synchronized**: Score variance $< 0.15$
- **Moderate Divergence**: Score variance $0.15 - 0.35$
- **Elevated Risk Drift**: Score variance $\ge 0.35$

---

### Q22: How does the system handle missing features when evaluating bank statement transactions?
**Answer**:
Bank statements do not record internal device hardware identifiers or real-time microsecond IP velocity. Rather than inventing fake numbers:
1. Available transaction attributes (`amount`, `timestamp`, `merchant`, `category`, `channel`, `city`) are extracted directly.
2. The 23-feature sliding window engine computes true sequential velocity, rolling spending, and entity frequency by replaying transactions chronologically.
3. Unobserved telemetry flags (e.g. `new_device_flag`) default to neutral baseline indicators without corrupting mathematical evaluation.

---

### Q23: What are the current architectural limitations of the project?
**Answer**:
1. **Storage Format**: Scanned, non-searchable PDF statements requiring Optical Character Recognition (OCR) are not natively parsed.
2. **Single-Node Model Execution**: While Kafka and Spark scale horizontally, model inference currently runs within the application process rather than a dedicated Triton or TorchServe cluster.
3. **No Dynamic Active Retraining**: Model weights are loaded from frozen serialized artifacts (`models/artifacts/`) and do not adapt automatically without retraining pipeline invocation.

---

### Q24: What is the future roadmap for FinStream AI?
**Answer**:
1. **Native PDF Table Extraction & OCR**: Integrate `pdfplumber` and Tesseract OCR to parse scanned and password-protected PDF bank statements.
2. **Role-Based Access Control (RBAC)**: Implement JWT authentication distinguishing Auditor, Fraud Analyst, and Administrator tiers.
3. **Cloud Infrastructure Deployment**: Automate deployment to AWS/GCP using Kubernetes (EKS/GKE) with distributed Kafka brokers.
4. **Active Learning Feedback Loop**: Allow analysts to confirm or dismiss fraud flags directly on `/transaction/{id}`, sending labeled feedback to an online retraining queue.
