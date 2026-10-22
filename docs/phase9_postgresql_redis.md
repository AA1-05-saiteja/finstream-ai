# Phase 9 — PostgreSQL + Redis Data Persistence Layer

This document details the architecture, relational schema, Redis key design, repository abstraction, and persistence lifecycle for **FinStream AI**.

---

## 1. Architecture Flow

```mermaid
flowchart TD
    A[Evaluated Transaction Stream\n(Phase 7/8 Inference + SHAP)] --> B[Persistence Service\n(database/persistence_service.py)]

    subgraph Relational Persistence [PostgreSQL - Durable System of Record]
        B --> C[Postgres Repository\n(database/repositories.py)]
        C --> D[(transactions Table\nImmutable Event History)]
        C --> E[(risk_assessments Table\nXGBoost + IF + Hybrid Score)]
        C --> F[(shap_explanations Table\nRanked Local Attributions)]
        D -. 1:1 .-> E
        E -. 1:N .-> F
    end

    subgraph Hot State Cache [Redis - Low-Latency Cache Layer]
        B --> G[Redis Repository\n(database/redis_client.py)]
        G --> H["finstream:risk:{tx_id}\n(Compact Risk Record)"]
        G --> I["finstream:account:{acc_id}:latest\n(Latest Account Snapshot)"]
        G --> J["finstream:tx:{tx_id}\n(Transaction Payload)"]
    end

    B --> K[Structured Persistence Result\nstatus: SUCCESS / FAILED]
    K --> L[Future Phase 10 FastAPI Backend\nREST & WebSockets]
```

---

## 2. PostgreSQL Relational Schema

### 2.1 `transactions` Table
Stores immutable financial event data with financial numeric precision and event-time tracking.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY`, `AUTOINCREMENT` | Internal synthetic sequence ID |
| `transaction_id` | `VARCHAR(64)` | `UNIQUE`, `NOT NULL`, `INDEX` | Unique transaction identifier (e.g. `TX000001`) |
| `timestamp` | `TIMESTAMPTZ` | `NOT NULL`, `INDEX` | Event-time timestamp |
| `account_id` | `VARCHAR(32)` | `NOT NULL`, `INDEX` | Originating account ID |
| `amount` | `NUMERIC(14, 2)` | `NOT NULL` | Monetary amount with exact decimal representation |
| `currency` | `VARCHAR(8)` | `DEFAULT 'INR'`, `NOT NULL` | Currency code |
| `merchant_id` | `VARCHAR(32)` | `NOT NULL` | Merchant identifier |
| `merchant_category` | `VARCHAR(64)` | `NOT NULL` | Vertical (e.g. `GROCERY`, `ELECTRONICS`) |
| `city` | `VARCHAR(64)` | `NOT NULL` | Location of transaction |
| `device_id` | `VARCHAR(64)` | `NOT NULL` | Originating device ID |
| `channel` | `VARCHAR(32)` | `NOT NULL` | Payment channel (`UPI`, `POS`, etc.) |
| `card_present` | `BOOLEAN` | `DEFAULT TRUE`, `NOT NULL` | Physical card present flag |
| `transaction_type` | `VARCHAR(32)` | `DEFAULT 'PURCHASE'`, `NOT NULL` | Event type |
| `scenario_label` | `VARCHAR(64)` | `DEFAULT 'NORMAL'`, `NOT NULL` | Synthetic generator scenario label |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT NOW()`, `NOT NULL` | Ingestion timestamp |

### 2.2 `risk_assessments` Table
Stores dual-model anomaly inference results and the hybrid risk metric.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY`, `AUTOINCREMENT` | Internal primary key |
| `transaction_id` | `VARCHAR(64)` | `FOREIGN KEY (transactions.transaction_id)`, `UNIQUE`, `INDEX` | Linked transaction |
| `xgboost_probability` | `FLOAT` | `NOT NULL` | Supervised XGBoost anomaly likelihood $[0, 1]$ |
| `isolation_forest_score` | `FLOAT` | `NOT NULL` | Raw inverted Isolation Forest decision score |
| `isolation_forest_normalized` | `FLOAT` | `NOT NULL` | Normalized Isolation Forest score $[0, 1]$ |
| `hybrid_risk_score` | `FLOAT` | `NOT NULL`, `INDEX` | Weighted score ($0.70 \times P_{\text{xgb}} + 0.30 \times S_{\text{if}}$) |
| `risk_level` | `VARCHAR(16)` | `NOT NULL`, `INDEX` | Categorical risk tier (`LOW`, `MEDIUM`, `HIGH`) |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT NOW()`, `NOT NULL` | Assessment timestamp |

### 2.3 `shap_explanations` Table
Stores normalized feature-level attributions explaining the XGBoost score.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY`, `AUTOINCREMENT` | Internal primary key |
| `risk_assessment_id` | `INTEGER` | `FOREIGN KEY (risk_assessments.id)`, `INDEX` | Linked risk assessment |
| `feature_name` | `VARCHAR(64)` | `NOT NULL` | Evaluated feature name |
| `feature_value` | `FLOAT` | `NOT NULL` | Observed value for the transaction |
| `shap_value` | `FLOAT` | `NOT NULL` | Raw SHAP attribution value |
| `absolute_shap_value` | `FLOAT` | `NOT NULL` | Absolute contribution magnitude |
| `direction` | `VARCHAR(32)` | `NOT NULL` | `increases_anomaly` or `decreases_anomaly` |
| `rank` | `INTEGER` | `NOT NULL` | Feature importance rank ($1 \dots N$) |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT NOW()`, `NOT NULL` | Insertion timestamp |

---

## 3. Redis Key Convention & Hot-State Design

| Key Pattern | Format | Default TTL | Description |
| :--- | :--- | :--- | :--- |
| `finstream:risk:{transaction_id}` | JSON string | 86,400s (24h) | Compact risk summary for fast lookup |
| `finstream:account:{account_id}:latest` | JSON string | 86,400s (24h) | Latest transaction & risk assessment for account |
| `finstream:tx:{transaction_id}` | JSON string | 3,600s (1h) | Raw transaction payload cache |

---

## 4. Error Tolerance & Consistency

1. **PostgreSQL as Source of Truth**:
   All database operations occur within an explicit `session_scope()` transaction block with automatic commit on success and rollback on any failure.

2. **Non-Blocking Cache Fallback**:
   If Redis becomes unreachable or times out, the `PersistenceService` logs a warning and flags `redis_cached = False`, but preserves the committed PostgreSQL record without failing the stream.

3. **Idempotency**:
   Transactions with duplicate `transaction_id`s are safely handled without duplicating records or causing primary key constraint violations.

---

## 5. CLI & Operational Commands

```powershell
# 1. Start Docker infrastructure (PostgreSQL & Redis)
docker compose up -d postgres redis

# 2. Check infrastructure connectivity
python -m database.init_db --check

# 3. Create / Initialize tables
python -m database.init_db

# 4. Reset development tables (Clears test data)
python -m database.init_db --reset
```
