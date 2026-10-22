# Phase 10 — FastAPI Backend REST API

This document details the REST API architecture, route definitions, schemas, error handling, dependency injection, and integration endpoints for **FinStream AI**.

---

## 1. Architecture Flow

```mermaid
flowchart TD
    subgraph Data & Storage Layer
        PG[(PostgreSQL\nTransactions, Risks, SHAP)]
        RD[(Redis\nHot State & Account Snapshots)]
    end

    subgraph Service Layer [backend/services.py]
        SRV[ApiService]
        SRV -->|Queries / Filters| PG
        SRV -->|Fast Cache Lookup| RD
    end

    subgraph FastAPI Application Layer [backend/main.py]
        DEP[FastAPI Dependency Injection\nbackend/dependencies.py]
        DEP --> SRV

        R_HEALTH[Health Router\n/api/v1/health]
        R_TX[Transactions Router\n/api/v1/transactions]
        R_RISK[Risks Router\n/api/v1/risks]
        R_ACC[Accounts Router\n/api/v1/accounts]

        R_HEALTH --> DEP
        R_TX --> DEP
        R_RISK --> DEP
        R_ACC --> DEP
    end

    subgraph Clients
        CLIENT[Future React + Vite Dashboard\n(Phase 11)]
        SWAGGER[OpenAPI Swagger UI\n/docs]
        CLIENT -->|REST Requests| R_TX
        CLIENT -->|REST Requests| R_RISK
        CLIENT -->|REST Requests| R_ACC
        SWAGGER -->|Interactive Testing| FastAPI
    end
```

---

## 2. API Endpoints Summary

| Method | Endpoint | Description | Query Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Basic API service operational health | None |
| `GET` | `/api/v1/health/dependencies` | Live connectivity status for PostgreSQL & Redis | None |
| `GET` | `/api/v1/transactions` | Paginated historical transaction stream | `limit`, `offset`, `account_id`, `start_time`, `end_time` |
| `GET` | `/api/v1/transactions/{id}` | Detailed transaction event, evaluated risk, and SHAP attributions | Path: `id` |
| `GET` | `/api/v1/risks` | Paginated anomaly risk records with tier filtering | `limit`, `offset`, `risk_level`, `account_id`, `start_time`, `end_time` |
| `GET` | `/api/v1/risks/{id}` | Dual-model risk scores for a single transaction | Path: `id` |
| `GET` | `/api/v1/risks/{id}/explanations` | Ranked SHAP local feature attributions | Path: `id` |
| `GET` | `/api/v1/accounts/{id}/risk` | Latest account risk state (Redis hot cache with PostgreSQL fallback) | Path: `id` |
| `GET` | `/api/v1/accounts/{id}/transactions` | Paginated transaction history for a specific account | `limit`, `offset`, `start_time`, `end_time` |

---

## 3. Pydantic Response Schemas

### 3.1 Transaction Detail Response (`/api/v1/transactions/{id}`)
```json
{
  "transaction": {
    "transaction_id": "TX000004",
    "timestamp": "2026-10-01T12:00:00Z",
    "account_id": "ACC0147",
    "amount": 350073.73,
    "currency": "INR",
    "merchant_id": "MERCH_88",
    "merchant_category": "JEWELRY",
    "city": "Mumbai",
    "device_id": "DEV_NEW",
    "channel": "NET_BANKING",
    "card_present": false,
    "transaction_type": "TRANSFER",
    "scenario_label": "HIGH_AMOUNT"
  },
  "risk": {
    "transaction_id": "TX000004",
    "xgboost_probability": 0.7948,
    "isolation_forest_score": 0.1848,
    "isolation_forest_normalized": 0.8370,
    "hybrid_risk_score": 0.8074,
    "risk_level": "HIGH"
  },
  "explanations": [
    {
      "feature": "amount",
      "feature_value": 350073.73,
      "shap_value": 0.9912,
      "absolute_shap_value": 0.9912,
      "direction": "increases_anomaly",
      "rank": 1
    }
  ]
}
```

### 3.2 Latest Account Risk Response (`/api/v1/accounts/{id}/risk`)
```json
{
  "account_id": "ACC0147",
  "transaction_id": "TX000004",
  "amount": 350073.73,
  "hybrid_risk_score": 0.8074,
  "risk_level": "HIGH",
  "xgboost_probability": 0.7948,
  "isolation_forest_normalized": 0.8370,
  "source": "redis_hot_state"
}
```

---

## 4. Error Handling & Standards

* **`404 Not Found`**: Returned when an ID does not exist:
  ```json
  {
    "error": "transaction_not_found",
    "message": "Transaction 'TX_INVALID' was not found."
  }
  ```
* **`422 Validation Error`**: Returned for invalid parameters (e.g., `risk_level=CRITICAL`, `limit=500`, `start_time > end_time`):
  ```json
  {
    "error": "invalid_request_parameters",
    "message": "start_time must be less than or equal to end_time"
  }
  ```

---

## 5. Operational Commands

```powershell
# Run the FastAPI server in development mode
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Interactive Documentation
# Swagger UI: http://localhost:8000/docs
# ReDoc:      http://localhost:8000/redoc
```
