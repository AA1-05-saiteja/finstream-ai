# FinStream AI — 3-Minute Live Academic Demonstration Script

This script provides an exact, step-by-step walkthrough for demonstrating the FinStream AI platform during a college project review, viva examination, or video recording.

---

## Pre-Demo Checklist (1 Minute Before Recording)

1. Open PowerShell in the project root:
   ```powershell
   .\venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```
2. Verify in your browser that the following URLs load cleanly:
   - Live Monitor: [http://localhost:8000/](http://localhost:8000/)
   - Statement Portal: [http://localhost:8000/statement](http://localhost:8000/statement)
   - Monthly Insights: [http://localhost:8000/insights](http://localhost:8000/insights)
   - Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
3. Ensure the demonstration sample files exist in `data/sample_data/`:
   - `normal_monthly_statement.csv`
   - `suspicious_anomalies_statement.xlsx`

---

## Step-by-Step Demonstration Sequence (Duration: 3 Minutes)

### Step 1: Real-Time Live Monitor & Baseline State (0:00 – 0:30)
- **URL**: [http://localhost:8000/](http://localhost:8000/)
- **Visual**: Show the dark-themed financial dashboard with real-time KPI metrics (Throughput, Anomaly Rate, Active Stream status).
- **Narration**:
  > *"FinStream AI is a real-time transaction intelligence platform combining dual-model machine learning and explainable AI. Here on the live dashboard, incoming financial transactions are evaluated on-the-fly across 23 streaming behavioral features."*

### Step 2: Toggle Live Streaming Mode (0:30 – 0:50)
- **Action**: In the top navigation bar, toggle the mode button from **`○ PAUSED`** to **`● LIVE MODE`**.
- **Visual**: Watch transactions tick automatically every 2.5 seconds. The transaction table appends incoming events, the live risk gauge oscillates, and the rolling throughput chart updates dynamically.
- **Narration**:
  > *"When LIVE MODE is enabled, transactions are ingested and scored in real time. Notice the explicit badge indicating 'LIVE TRANSACTION STREAM' to maintain strict data provenance."*

### Step 3: Trigger High-Risk Scenario & Anomaly Banner (0:50 – 1:15)
- **Action**: In the **Interactive Transaction Simulator** control panel, select the scenario **`High Amount & Velocity Outlier`** and click **`Simulate Transaction`**.
- **Visual**: 
  - An evaluated transaction with a hybrid score $\ge 0.70$ arrives.
  - The prominent high-contrast banner triggers immediately at the top of the screen:
    `⚠ HIGH-RISK TRANSACTION DETECTED: [Tx ID | Amount | Risk Score | Timestamp]`
- **Narration**:
  > *"The dual ML engine immediately detected a high-risk anomaly. The alert banner triggers in real time with the transaction ID, amount, and hybrid risk score."*

### Step 4: Transaction Deep Dive & Explainable AI (1:15 – 1:45)
- **Action**: Click the **`Investigate`** button on the high-risk alert banner.
- **Visual**: The browser navigates to `/transaction/{id}`. Show:
  1. **Dual Model Breakdown**: Supervised XGBoost probability ($P_{\text{xgb}}$) vs. Unsupervised Isolation Forest score ($S_{\text{if\_norm}}$).
  2. **23 Engineered Features**: Display the feature table (velocity counters, 1h spending peaks, device/city frequency).
  3. **SHAP TreeExplainer Chart**: Highlight the horizontal waterfall bar chart displaying which exact features pushed the score into high risk.
- **Narration**:
  > *"Under financial transparency regulations, black-box decisions are unacceptable. Our SHAP TreeExplainer calculates the exact mathematical feature attributions. Here, the top driver is a sudden spending surge exceeding the account's 1-hour average by 800%."*

### Step 5: Bank Statement Intelligence Upload (1:45 – 2:15)
- **Action**: Navigate to [http://localhost:8000/statement](http://localhost:8000/statement). Drag and drop `data/sample_data/normal_monthly_statement.csv` into the upload zone (or click `Upload & Analyze`).
- **Visual**: Show:
  - **Data Quality Audit Card**: Original rows (31), valid transactions (31), dropped duplicates (0), and parsed date range.
  - **9 Financial & Risk KPI Cards**: Total Debits, Total Credits, Highest/Lowest Amount, and Risk Counts (Low, Medium, High).
- **Narration**:
  > *"In addition to streaming transactions, FinStream AI features a zero-cloud Bank Statement Intelligence engine. Users can upload standard CSV or Excel statements. It automatically maps column headers, deduplicates entries, masks account numbers for privacy, and scores every transaction sequentially through the ML model."*

### Step 6: Risk Ranking Separation (2:15 – 2:35)
- **Visual**: Scroll down the statement page to highlight the 3 distinct risk sections:
  - 🔴 **Highest Risk Transactions** (Detailed cards with top contributing SHAP factors and "View Details" button).
  - 🟡 **Medium Risk Transactions**
  - 🟢 **Lowest Risk Transactions**
- **Narration**:
  > *"The system strictly distinguishes between financial ranking (highest rupee amounts) and risk ranking (highest anomaly probability). A large salary credit is financially high but low risk, whereas a smaller rapid off-hour debit is flagged as anomalous."*

### Step 7: Monthly Spending Insights & Contextual Drift (2:35 – 2:50)
- **Action**: Click **`Monthly Insights`** or open [http://localhost:8000/insights](http://localhost:8000/insights).
- **Visual**: Show the 30-Day dual-axis spending vs. risk trend chart and the category risk posture breakdown table.
- **Narration**:
  > *"The Insights portal provides monthly spending timelines and category risk postures. Furthermore, this uploaded statement now forms the historical baseline for our Contextual Drift card on the home screen."*

### Step 8: Multi-Sheet Excel Export & Wrap-Up (2:50 – 3:00)
- **Action**: Return to `/statement` and click **`Download Analysis Report (XLSX)`**.
- **Narration**:
  > *"Analysts can export the complete evaluated statement as a multi-sheet Excel workbook. FinStream AI is completely verified with 113 automated unit tests, sub-30ms latency, and 0.9676 ROC-AUC."*
