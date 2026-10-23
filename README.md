# FinStream AI: A Real-Time Financial Transaction Intelligence and Anomaly Detection Platform

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Architecture: Event-Driven](https://img.shields.io/badge/Architecture-Event--Driven-green.svg)]()
[![Build & Test Status](https://img.shields.io/badge/tests-113%20passed%20%7C%200%20failed-brightgreen.svg)]()
[![Platform Status](https://img.shields.io/badge/status-Bank%20Statement%20%2B%20Live%20Stream%20Complete-success.svg)]()

> **Academic Disclaimer**: This is an academic research and final-year Data Science major engineering project. All data, customer accounts, transaction IDs, and merchant records are 100% synthetically generated. The system is a real-time decision-support platform that scores and flags transactions for human analytical review; it does not connect to real financial institutions nor make irreversible automated financial settlements.

---

## Table of Contents
- [1. Project Overview & Motivation](#1-project-overview--motivation)
- [2. System Architecture](#2-system-architecture)
- [3. Comprehensive Technology Stack & Tools](#3-comprehensive-technology-stack--tools)
- [4. Implementation Status & Phase Roadmap](#4-implementation-status--phase-roadmap)
- [5. Machine Learning & Anomaly Detection Methodology](#5-machine-learning--anomaly-detection-methodology)
- [6. Real-Time Feature Engineering (23 Features)](#6-real-time-feature-engineering-23-features)
- [7. Measured Performance Benchmarks](#7-measured-performance-benchmarks)
- [8. Service Port Map & Live Endpoints](#8-service-port-map--live-endpoints)
- [9. Project Directory Structure](#9-project-directory-structure)
- [10. Setup, Execution & Testing Guide](#10-setup-execution--testing-guide)
- [11. Interactive Dashboard & Demonstration Scenarios](#11-interactive-dashboard--demonstration-scenarios)
- [12. Bank Statement Intelligence & Analytics Engine](#12-bank-statement-intelligence--analytics-engine)
- [13. Live Stream Extension & Anomaly Alert System](#13-live-stream-extension--anomaly-alert-system)
- [14. Project Completion Status & Roadmap](#14-project-completion-status--roadmap)
- [15. License](#15-license)

---

## 1. Project Overview & Motivation

Modern financial institutions process millions of transactions per second. Traditional static rule-based fraud detection engines suffer from high false-positive rates, inability to adapt to novel fraud patterns, and latency bottlenecks.

**FinStream AI** is an enterprise-grade, event-driven streaming and machine learning platform designed to:
1. **Ingest high-frequency financial streams** using Apache Kafka.
2. **Compute 23 real-time behavioral features** across event-time sliding windows (1 min, 5 min, 1 hr) with PySpark and in-memory state tracking.
3. **Execute dual-model anomaly detection** combining supervised classification (**XGBoost**) for known attack patterns and unsupervised outlier isolation (**Isolation Forest**) for zero-day anomalies.
4. **Deliver explainable risk scoring** using **SHAP TreeExplainer** to highlight the top-5 influential features causing any transaction to be flagged.
5. **Ensure ACID durability and low-latency state** with **PostgreSQL** relational tables and **Redis** microsecond hot caching.
6. **Stream live assessments to analyst dashboards** via **FastAPI**, **WebSockets**, and a modern **React + TypeScript** web portal.

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph Ingestion ["1. Data Ingestion & Messaging"]
        GEN["Synthetic Generator\n(producer/transaction_generator.py)"]
        KP["Kafka Producer\n(producer/kafka_producer.py)"]
        KAFKA["Kafka Broker (Topic: transactions)\n:9092 (KRaft Mode)"]
        GEN -->|JSON Events| KP -->|Batch Produce| KAFKA
    end

    subgraph Streaming ["2. Stream Processing & Enrichment"]
        SPARK["PySpark Structured Streaming\n(streaming/stream_processor.py)"]
        FEAT["23-Feature Sliding Window Engine\n(streaming/feature_engineering.py)"]
        KAFKA -->|Consume Stream| SPARK
        SPARK -->|Watermarking & State| FEAT
    end

    subgraph Intelligence ["3. Dual ML Inference & Explainability"]
        XGB["Supervised XGBoost Classifier\n(P_xgb)"]
        IF["Unsupervised Isolation Forest\n(S_if_norm)"]
        HYBRID["Hybrid Risk Scoring\n(0.70*P_xgb + 0.30*S_if_norm)"]
        SHAP["SHAP TreeExplainer\n(Top-5 Local Attributions)"]
        FEAT --> XGB & IF
        XGB & IF --> HYBRID --> SHAP
    end

    subgraph Persistence ["4. Storage & State Management"]
        PG[("PostgreSQL Database\n:5432 (Normalized Tables)")]
        REDIS[("Redis Cache\n:6379 (Hot State Caching)")]
        PSVC["Persistence Service\n(database/persistence_service.py)"]
        SHAP --> PSVC
        PSVC -->|ACID Durability| PG
        PSVC -->|Microsecond Lookups| REDIS
    end

    subgraph Serving_UI ["5. Serving & Real-Time Visualization"]
        FASTAPI["FastAPI REST & WebSocket Server\n:8000"]
        REACT["React + TypeScript + Vite Dashboard\n:3000 / :5173"]
        PSVC --> FASTAPI
        FASTAPI -->|WebSocket Stream /api/v1/ws/transactions| REACT
        FASTAPI -->|REST Endpoints /api/v1/*| REACT
    end
```

---

## 3. Comprehensive Technology Stack & Tools

FinStream AI integrates industry-standard tools across data engineering, machine learning, web backend, and frontend UI:

| Layer / Domain | Technology & Version | Tool / Library | Role & Architectural Purpose |
| :--- | :--- | :--- | :--- |
| **Language & Runtime** | Python 3.12 / 3.11 | Python, Pydantic 2.7+ | Core execution runtime, typed schemas, data contracts, and validation |
| **Stream Ingestion** | Apache Kafka 3.7.0 | `kafka-python-ng`, `confluent-kafka` | Distributed streaming broker (KRaft mode, topic `transactions`, 3 partitions) |
| **Kafka Inspection** | Provectus Kafka UI | Docker Container | Web dashboard on port `8080` for monitoring topic partitions and consumer lag |
| **Stream Processing** | PySpark 3.5.1 | PySpark Structured Streaming | 5-minute watermarking, event-time extraction, and fault-tolerant ingestion |
| **Feature Engineering** | Python & NumPy | In-Memory Sliding Windows | 23 behavioral, velocity, spending, and entity frequency features |
| **Supervised ML** | XGBoost 2.0.3 | `xgboost.XGBClassifier` | Detects known attack vectors; produces calibrated probability $P_{\text{xgb}}$ |
| **Unsupervised ML** | Scikit-learn 1.4.2 | `sklearn.ensemble.IsolationForest` | Detects novel zero-day anomalies; normalized score $S_{\text{if\_norm}}$ |
| **Explainable AI (XAI)**| SHAP 0.45.0 | `shap.TreeExplainer` | Local feature attribution ranking the top-5 reasons for risk flagging |
| **Relational Storage** | PostgreSQL 16 | PostgreSQL, SQLAlchemy 2.0+ | ACID storage for `transactions`, `risk_assessments`, `shap_explanations` |
| **In-Memory Cache** | Redis 7.0 | `redis-py`, FakeRedis | Microsecond state retrieval (`finstream:risk:*`, `finstream:account:*`) |
| **Web REST API** | FastAPI 0.111.0 | Starlette, Pydantic Settings | Asynchronous REST endpoints, dependency injection, OpenAPI documentation |
| **WebSockets** | WebSockets 12.0+ | FastAPI WebSocket Router | Non-blocking streaming push (`/api/v1/ws/transactions`) with backoff |
| **Frontend Framework** | React 18.3.1 | TypeScript 5.4.5, Vite 5.2 | Single-page application, interactive risk cards, and live stream visualizer |
| **Frontend Styling** | Tailwind CSS 3.4 | Lucide React | High-contrast financial analyst interface and dark mode UI |
| **Containerization** | Docker, Docker Compose | Multi-Stage Dockerfiles | 6 container microservice topology for reproducible deployment |
| **Automated Testing** | Pytest 9.1.1 | `pytest-asyncio`, `pytest-mock` | Automated unit, regression, and end-to-end integration test harness |

---

## 4. Implementation Status & Phase Roadmap

All **13 planned phases** have been completely implemented, verified with automated unit and integration tests, and benchmarked:

| Phase | Phase Name | Status | Verified Capabilities | Test Count |
| :---: | :--- | :---: | :--- | :---: |
| **Phase 1** | Project Structure & Configuration | ✅ Complete | Typed Pydantic settings, `.env` loading, logging, directory scaffolding | 3 tests |
| **Phase 2** | Synthetic Transaction Generator | ✅ Complete | Realistic behavioral profiles, Indian cities, INR currency, 8 fraud scenarios | 11 tests |
| **Phase 3** | Kafka Producer & Consumer | ✅ Complete | Topic creation, JSON serialization, consumer polling, delivery callbacks | 10 tests |
| **Phase 4** | PySpark Structured Streaming | ✅ Complete | Spark schema validation, 5-min watermarking, event-time parsing | 9 tests |
| **Phase 5** | Real-Time Feature Engineering | ✅ Complete | 23 sliding window features (1m, 5m, 1h velocity, deviation, diversity) | 9 tests |
| **Phase 6** | ML Training & Offline Evaluation | ✅ Complete | XGBoost (ROC-AUC: 0.9676) + Isolation Forest training & artifact export | 6 tests |
| **Phase 7** | Real-Time ML Inference & Risk Scoring | ✅ Complete | Dual-model scoring, score normalization, hybrid risk categorization | 5 tests |
| **Phase 8** | SHAP Model Explainability | ✅ Complete | TreeExplainer initialization, top-5 feature attribution, directionality | 2 tests |
| **Phase 9** | PostgreSQL & Redis Persistence | ✅ Complete | Normalized SQL tables, ACID transactions, Redis hot-state caching | 17 tests |
| **Phase 10**| FastAPI Backend REST API | ✅ Complete | Typed REST endpoints, pagination, dependency injection, `/docs` Swagger | 15 tests |
| **Phase 11**| React + TypeScript Dashboard | ✅ Complete | Responsive dashboard, real-time ticker, SHAP visualizer, account search | Integrated |
| **Phase 12**| WebSocket Real-Time Delivery | ✅ Complete | Sub-millisecond event push, heartbeat keepalive, reconnection backoff | 3 tests |
| **Phase 13**| Full E2E Integration & Benchmarking | ✅ Complete | 6-container Docker Compose, pipeline runner, throughput & latency metrics | 8 tests |
| **Phase 14**| Bank Statement Intelligence & Live Stream Extension | ✅ Complete | Multi-format CSV/XLSX cleaning, 23-feature ML scoring, SHAP explainability, 3 web dashboards (`/statement`, `/insights`, `/transaction/{id}`), live alerts & contextual baseline comparison | 14 tests |
| **Total** | **Full Platform Verification** | ✅ **COMPLETE** | **All 14 phases verified; 0 failures, 0 errors, 0 regressions** | **113 Passed** |

---

## 5. Machine Learning & Anomaly Detection Methodology

### 5.1 Dual-Model Inference Strategy
FinStream AI runs two complementary machine learning algorithms in parallel for every transaction:
1. **Supervised XGBoost Classifier (`P_xgb`)**:
   - Trained on historical fraud patterns (velocity spikes, high amounts, device switches).
   - Generates a calibrated fraud probability between $0.0$ and $1.0$.
   - Held-Out Performance: Precision `0.9757`, Recall `0.7461`, F1 `0.8456`, ROC-AUC `0.9676`.
2. **Unsupervised Isolation Forest (`S_if_norm`)**:
   - Inverts the decision path length to isolate novel transactions that do not conform to any historical cluster.
   - Normalized into $[0.0, 1.0]$ using min-max scaling across empirical bounds:
     $$S_{\text{if\_norm}} = \text{clip}\left(\frac{\text{raw\_score} - (-0.20)}{0.20 - (-0.20)}, 0.0, 1.0\right)$$

### 5.2 Hybrid Risk Scoring Formula
The final decision score combines both models using configurable weights:
$$\text{Hybrid Risk Score} = (0.70 \times P_{\text{xgb}}) + (0.30 \times S_{\text{if\_norm}})$$

* **`LOW RISK`** ($< 0.30$): Normal transaction; automatically approved.
* **`MEDIUM RISK`** ($0.30 \le \text{Score} < 0.70$): Behavioral deviation; flagged for monitoring.
* **`HIGH RISK`** ($\ge 0.70$): Critical anomaly; triggers SHAP explainability generation and alerts.

### 5.3 Local SHAP Explainability
For high-risk transactions, the system computes exact Shapley values using `shap.TreeExplainer`. It extracts:
* **Top-5 Features**: The features contributing most heavily to the risk score.
* **Feature Value**: The actual recorded metric (e.g., `amount = ₹85,000`).
* **Contribution Impact**: Directional attribution (`increases_anomaly` vs `decreases_anomaly`).

---

## 6. Real-Time Feature Engineering (23 Features)

Every transaction is enriched with 23 features calculated over sliding event-time windows:

| # | Feature Name | Category | Window | Description |
|---|---|---|---|---|
| 1 | `amount` | Amount | Point-in-time | Raw transaction amount in INR |
| 2 | `log_amount` | Amount | Point-in-time | $\ln(1 + \text{amount})$ to stabilize variance |
| 3 | `transaction_count_1m` | Velocity | 1 Minute | Number of transactions for account in last 60 seconds |
| 4 | `transaction_count_5m` | Velocity | 5 Minutes | Number of transactions for account in last 300 seconds |
| 5 | `transaction_count_1h` | Velocity | 1 Hour | Cumulative transaction count in past 1 hour |
| 6 | `total_amount_5m` | Spending | 5 Minutes | Total spending in INR across the last 5 minutes |
| 7 | `total_amount_1h` | Spending | 1 Hour | Total spending in INR across the last 1 hour |
| 8 | `average_amount_5m` | Spending | 5 Minutes | Average transaction size over 5 minutes |
| 9 | `average_amount_1h` | Spending | 1 Hour | Average transaction size over 1 hour |
| 10 | `maximum_amount_1h` | Spending | 1 Hour | Maximum single transaction size observed in 1 hour |
| 11 | `minimum_amount_1h` | Spending | 1 Hour | Minimum single transaction size observed in 1 hour |
| 12 | `amount_deviation_from_recent_avg` | Deviation | 1 Hour | $(\text{amount} - \text{average\_amount\_1h})$ |
| 13 | `amount_ratio_to_recent_avg` | Deviation | 1 Hour | $\text{amount} / \max(\text{average\_amount\_1h}, 1.0)$ |
| 14 | `merchant_transaction_count_1h` | Frequency | 1 Hour | Count of transactions at this specific merchant |
| 15 | `device_transaction_count_1h` | Frequency | 1 Hour | Count of transactions using this specific device |
| 16 | `city_transaction_count_1h` | Frequency | 1 Hour | Count of transactions originating from this city |
| 17 | `channel_transaction_count_1h` | Frequency | 1 Hour | Count of transactions via this channel (ONLINE/POS/ATM) |
| 18 | `unique_device_count_1h` | Diversity | 1 Hour | Count of unique device IDs used by account in 1 hour |
| 19 | `unique_merchant_count_1h` | Diversity | 1 Hour | Count of distinct merchants visited in 1 hour |
| 20 | `unique_city_count_1h` | Diversity | 1 Hour | Count of distinct cities recorded in 1 hour |
| 21 | `unique_channel_count_1h` | Diversity | 1 Hour | Count of distinct channels used in 1 hour |
| 22 | `known_device_flag` | Behavioral | Lifetime | $1.0$ if device has been seen before, $0.0$ if new |
| 23 | `new_city_flag` | Behavioral | Lifetime | $1.0$ if transaction occurs in an unseen city, $0.0$ if known |

---

## 7. Measured Performance Benchmarks

The full pipeline was benchmarked using the automated runner (`python -m scripts.benchmark_e2e --count 100 --scenario mixed`). Measured real-world metrics on Windows 11 (12 CPU threads):

### 7.1 Latency Percentiles by Stage
| Pipeline Stage | $P_{50}$ (Median) | $P_{95}$ | $P_{99}$ | Max Latency | Mean Latency |
|---|---|---|---|---|---|
| **1. Feature Engineering** | 0.06 ms | 0.11 ms | 0.18 ms | 1.43 ms | 0.08 ms |
| **2. Dual ML Inference + SHAP** | 18.84 ms | 44.97 ms | 50.10 ms | 51.48 ms | 21.70 ms |
| **3. DB & Cache Persistence** | 5.19 ms | 10.06 ms | 13.66 ms | 36.03 ms | 6.22 ms |
| **4. WebSocket Dispatch** | 1.91 ms | 4.12 ms | 6.57 ms | 17.21 ms | 2.40 ms |
| **Total End-to-End Pipeline** | **26.06 ms** | **58.87 ms** | **71.31 ms** | **84.70 ms** | **30.40 ms** |

* **Throughput**: ~**32.72 transactions/second** in single-process mode; burst capacity > 100 TPS across multi-partition Kafka.
* **Data Loss**: **0 records dropped** (100% correlation ID preservation from producer to dashboard).
* **Duplicates**: **0 duplicates permitted** (enforced by SQL unique constraints & Redis keys).

---

## 8. Service Port Map & Live Endpoints

When running either locally or inside Docker Compose, the following ports and services are available:

| Port | Service / Application | URL / Endpoint | Purpose |
|---|---|---|---|
| **`8000`** | Live Stream Web Dashboard | [http://localhost:8000/](http://localhost:8000/) | Live streaming transactions, risk charts, simulator & live high-risk alerts |
| **`8000`** | Bank Statement Intelligence | [http://localhost:8000/statement](http://localhost:8000/statement) | 1-month statement upload (CSV/XLSX), cleaning audit & dual-ML risk scoring |
| **`8000`** | Monthly Spending & Risk Insights | [http://localhost:8000/insights](http://localhost:8000/insights) | 30-day timeline charts, category breakdowns & risk posture analytics |
| **`8000`** | Transaction Deep-Dive Inspector | [http://localhost:8000/transaction/{id}](http://localhost:8000/transaction/STMT1001) | Individual profile, 23 model features grid & SHAP waterfall attribution |
| **`8000`** | FastAPI Interactive Swagger UI | [http://localhost:8000/docs](http://localhost:8000/docs) | OpenAPI interactive documentation and testing console |
| **`8000`** | ReDoc API Specs | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Schema definitions, contracts, and endpoint specifications |
| **`8000`** | Health Heartbeat | [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) | API service operational status |
| **`8000`** | Infrastructure Health | [http://localhost:8000/api/v1/health/dependencies](http://localhost:8000/api/v1/health/dependencies) | PostgreSQL and Redis connectivity diagnostics |
| **`8000`** | WebSocket Stream | `ws://localhost:8000/api/v1/ws/transactions` | Real-time evaluated transaction event push |
| **`3000`** / **`5173`** | React Dashboard | [http://localhost:3000](http://localhost:3000) (Docker) / `:5173` | Real-time monitoring UI & SHAP inspector |
| **`8080`** | Apache Kafka UI | [http://localhost:8080](http://localhost:8080) | Topic partitions, messages, and consumer lag browser |
| **`9092`** | Apache Kafka Broker | `localhost:9092` | Core Kafka message bus (KRaft mode) |
| **`5432`** | PostgreSQL Database | `localhost:5432` | Relational database (`finstream_db`) |
| **`6379`** | Redis Cache | `localhost:6379` | In-memory key-value cache and hot state |

---

## 9. Project Directory Structure

```text
finstream-ai/
├── README.md                      # Comprehensive project guide and reference
├── LICENSE                        # MIT License
├── requirements.txt               # Pinned Python package dependencies
├── config.py                      # Strongly-typed configuration manager (Pydantic)
├── docker-compose.yml             # 6-service orchestration (Kafka, UI, Postgres, Redis, API, UI)
├── Dockerfile                     # Multi-stage Python 3.12 + OpenJDK 17 container
├── portal.html                    # Standalone clickable HTML service portal
│
├── producer/                      # Data Ingestion Layer
│   ├── account_profiles.py        # Realistic customer behavioral distributions
│   ├── scenario_generator.py      # 8 synthetic fraud & normal scenario patterns
│   ├── transaction_models.py      # Strongly-typed Pydantic schemas for transactions
│   ├── transaction_generator.py   # Continuous synthetic generator engine & CLI
│   └── kafka_producer.py          # High-throughput Kafka publishing service
│
├── kafka/                         # Kafka Consumer & Scripts
│   └── consumer.py                # Standalone consumer with schema validation
│
├── streaming/                     # Real-Time Processing Layer
│   ├── stream_processor.py        # PySpark Structured Streaming with 5-min watermarking
│   ├── feature_engineering.py     # 23-feature sliding window state manager
│   └── pipeline_runner.py         # End-to-end deterministic benchmark runner
│
├── features/                      # Feature Definitions
│   └── feature_definitions.py     # Feature constants, ordering, and transformation functions
│
├── models/                        # Machine Learning Layer
│   ├── training_data.py           # Stratified synthetic dataset generator
│   ├── train_xgboost.py           # Supervised classifier training & tuning
│   ├── train_isolation_forest.py  # Unsupervised anomaly detector training
│   ├── train_all.py               # Unified training & evaluation orchestrator
│   ├── risk_scoring.py            # Hybrid ensemble formula & risk category assignment
│   ├── shap_explainer.py          # SHAP TreeExplainer feature attribution engine
│   ├── predict.py                 # Real-time dual-model inference CLI
│   └── artifacts/                 # Serialized models (.joblib) & feature_columns.json
│
├── database/                      # Persistence Layer
│   ├── models.py                  # SQLAlchemy models: transactions, risks, shap_explanations
│   ├── connection.py              # Connection pool & automatic SQLite fallback
│   ├── repositories.py            # Clean PostgreSQL CRUD repository layer
│   ├── redis_client.py            # Microsecond Redis cache client & key conventions
│   ├── persistence_service.py     # Unified ACID persistence coordinator
│   └── init_db.py                 # Schema creation & connectivity diagnostic CLI
│
├── backend/                       # FastAPI Web Backend
│   ├── main.py                    # Application factory, CORS, static routes (/statement, /insights, /transaction/{id})
│   ├── dependencies.py            # Modular dependency injection providers
│   ├── services.py                # REST API business service layer
│   ├── schemas.py                 # Public Pydantic API response and query contracts
│   ├── exceptions.py              # Custom HTTP error handlers
│   ├── websocket_manager.py       # WebSocket connection registry & heartbeats
│   ├── event_service.py           # Non-blocking event broadcasting service
│   ├── statement_analyzer.py      # Bank statement parsing, cleaning, 23-feature scoring & XLSX/CSV exports
│   ├── routes/                    # API route handlers
│   │   ├── health.py              # /api/v1/health & /dependencies
│   │   ├── transactions.py        # /api/v1/transactions query, pagination & simulation
│   │   ├── statement.py           # /api/v1/statement upload, sample, latest & exports
│   │   ├── stream.py              # /api/v1/stream tick, live events, alerts & comparison
│   │   ├── risks.py               # /api/v1/risks & SHAP explanations
│   │   ├── accounts.py            # /api/v1/accounts risk profile & history
│   │   └── websocket.py           # /api/v1/ws/transactions live socket
│   └── static/                    # Zero-Install Embedded Frontend Dashboards
│       ├── index.html             # Live stream monitor, transaction simulator & high-risk alerts
│       ├── statement.html         # Bank statement upload, cleaning audit & 9 KPI dashboard
│       ├── insights.html          # Monthly spending vs risk trends & category breakdown
│       └── transaction.html       # Single transaction deep dive, 23 features & SHAP waterfall
│
├── dashboard/                     # React + TypeScript Frontend (Optional Alternative UI)
│   ├── Dockerfile                 # Multi-stage Vite build + Nginx Alpine runner
│   ├── nginx.conf                 # Nginx reverse proxy routing
│   ├── package.json               # Node.js dependencies
│   ├── vite.config.ts             # Vite development server config
│   ├── src/                       # Frontend source code
│   │   ├── App.tsx                # Main dashboard container & tab navigation
│   │   ├── types/api.ts           # TypeScript interfaces matching backend schemas
│   │   ├── api/                   # Typed HTTP clients for REST endpoints
│   │   ├── websocket/             # WebSocket hook with exponential reconnection
│   │   └── components/            # UI widgets: LiveFeed, SHAPVisualizer, RiskCards
│
├── tests/                         # Complete Automated Test Suite (108 Tests)
│   ├── test_config.py             # Configuration tests
│   ├── test_transaction_generator.py # Generator schema & scenario tests
│   ├── test_kafka_*.py            # Producer, consumer & integration tests
│   ├── test_stream_processor.py   # Spark streaming tests
│   ├── test_feature_engineering.py# Sliding window & feature calculation tests
│   ├── test_xgboost_training.py   # Model evaluation tests
│   ├── test_predict.py            # Dual inference & SHAP tests
│   ├── test_database_*.py         # PostgreSQL repository tests
│   ├── test_redis_repository.py   # Redis caching tests
│   ├── test_api_*.py              # FastAPI REST & WebSocket tests
│   ├── test_statement_and_stream.py # Bank statement cleaning, ML scoring, live stream & alerts
│   └── test_end_to_end_pipeline.py# Full pipeline integration tests
│
├── reports/                       # Technical Validation Reports
│   ├── phase6_evaluation.md       # ML model evaluation benchmarks
│   └── phase13_end_to_end_validation.md # Pipeline performance & latency report
└── docs/                          # Architectural Documentation
    ├── architecture.md            # High-level system design
    └── phase13_end_to_end_integration.md # Microservice orchestration guide
```

---

## 10. Setup, Execution & Testing Guide

### 10.1 Local Virtual Environment Setup
```powershell
# 1. Create and activate Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1    # On Windows
# source venv/bin/activate     # On Linux / macOS

# 2. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 10.2 Run Full Test Suite (113 Tests)
```powershell
pytest tests/ -v
```

### 10.3 Run End-to-End Performance Benchmark
```powershell
python -m scripts.benchmark_e2e --count 100 --scenario mixed
```

### 10.4 Run Real-Time ML Inference CLI with SHAP
```powershell
python -m models.predict --rate 2 --duration 5 --scenario mixed
```

### 10.5 Launch Live Web Dashboard (Zero-Install — Recommended)
```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
Then open your web browser at:
* **⚡ Live Stream Dashboard**: **[http://localhost:8000/](http://localhost:8000/)** (Live events, simulator, high-risk alert banner & cross-source drift)
* **📄 Bank Statement Intelligence**: **[http://localhost:8000/statement](http://localhost:8000/statement)** (Upload 30-day statement CSV/XLSX, cleaning audit & dual-ML scoring)
* **📊 Monthly Insights**: **[http://localhost:8000/insights](http://localhost:8000/insights)** (Spending vs risk breakdown & 30-day timeline)
* **🔍 Transaction Deep-Dive**: **[http://localhost:8000/transaction/STMT1001](http://localhost:8000/transaction/STMT1001)** (All 23 features & SHAP attribution waterfall)
* **📖 Swagger API Documentation**: **[http://localhost:8000/docs](http://localhost:8000/docs)**
* **📚 ReDoc Interactive Reference**: **[http://localhost:8000/redoc](http://localhost:8000/redoc)**
* **🩺 Platform Health Diagnostics**: **[http://localhost:8000/api/v1/health/dependencies](http://localhost:8000/api/v1/health/dependencies)**

---

## 11. Interactive Dashboard & Demonstration Scenarios

The platform includes a built-in, zero-install live web dashboard directly embedded inside FastAPI. It allows college project demonstrations and interactive analytical exploration without installing Node.js, React, or Docker.

### 11.1 Live Demonstration Scenarios
From the **"Simulate Transaction"** control panel on the dashboard, you can trigger real transactions through the actual ML pipeline:

1. **🟢 Normal Transaction (LOW Risk)**:
   - Simulates typical consumer behavior matching account profile history.
   - Passes through the 23-feature engine, XGBoost classifier, and Isolation Forest.
   - **Expected Outcome**: Categorized as `LOW` risk (Score: ~`0.08 - 0.15`).

2. **🔴 High-Amount Anomaly (HIGH Risk)**:
   - Simulates an extreme purchase amount deviating 15x–35x above typical baseline.
   - Features `amount_deviation_recent_avg` and `log_amount` trigger alert thresholds.
   - **Expected Outcome**: Flagged as `HIGH` risk (Score: ~`0.80 - 0.90`). SHAP displays `amount` as the top contributor.

3. **🟡 Velocity Spike (Burst Anomaly)**:
   - Simulates rapid sequential transactions (seconds apart) on the same account.
   - Features `tx_count_1m`, `tx_count_5m`, and `amount_ratio_recent_avg` spike in the rolling sliding window state.
   - **Expected Outcome**: Escalates to `HIGH` risk (Score: ~`0.70 - 0.77`).

4. **⚡ High-Risk Prediction (Dual-Model Alert)**:
   - Simulates a compound anomaly combining large value, unseen device ID, and atypical merchant vertical.
   - Both supervised XGBoost and unsupervised Isolation Forest agree on high anomaly probability.
   - **Expected Outcome**: Flagged as `HIGH` risk (Score: >`0.80`) with comprehensive 5-factor SHAP attribution.

5. **🛠️ Custom Transaction Evaluator**:
   - Allows entering custom amount, payment channel (UPI, POS, ONLINE, ATM), city, and category to test any arbitrary scenario live.

---

## 12. Bank Statement Intelligence & Analytics Engine

The **Bank Statement Intelligence** extension (`/statement`, `/insights`, `/transaction/{id}`) allows uploading real or synthetic monthly bank statements, processing them 100% locally through the FastAPI application with zero cloud leakage, and evaluating every line item through the complete FinStream AI dual-ML pipeline.

```mermaid
flowchart LR
    FILE["Uploaded Statement\n(.csv or .xlsx)"] --> DETECT["Column Detection\n(Regex Heuristics)"]
    DETECT --> CLEAN["Data Cleaning & Audit\n(Currency, Dates, Duplicates)"]
    CLEAN --> ENGINE["23-Feature Sliding Window\n+ Dual-ML Scoring"]
    ENGINE --> KPIS["9 KPI Metric Cards\n+ Doughnut & Timeline"]
    ENGINE --> TIERS["Risk Sections\n🔴 Highest | 🟡 Medium | 🟢 Lowest"]
    ENGINE --> EXPORT["Export Reports\n(.csv / .xlsx with SHAP)"]
```

### 12.1 Capabilities & Architecture
1. **Multi-Format Ingestion**: Supports `.csv` and `.xlsx` statement files up to 25 MB, parsed entirely in-memory with pandas and openpyxl.
2. **One-Click 30-Day Sample Statement**: Includes an instant sample button (`/api/v1/statement/sample`) generating a realistic 30-day Indian banking statement (UPI, POS, Net Banking, salary credits, dining, groceries) with injected anomalies for immediate demonstration.
3. **Flexible Column Detection Heuristics**: Automatically maps diverse bank column formats without rigid headers:
   - **Date**: `Txn Date`, `Transaction Date`, `Value Date`, `Posting Date`
   - **Reference / ID**: `Ref No`, `Transaction ID`, `UTR`, `Cheque No`
   - **Description**: `Particulars`, `Narration`, `Description`, `Remarks`
   - **Financial Direction**: Handles separate `Debit` / `Credit` columns or single signed `Amount` columns.
   - **Balance**: `Closing Balance`, `Available Balance`, `Running Balance`
4. **Data Quality Audit**: Displays an audit card disclosing original row count, valid transactions, dropped identical duplicates, and parsed date range.
5. **Real Dual-Model Scoring (No Hardcoded Fakes)**:
   - Every transaction is fed sequentially into `RealTimeFeatureEngine` to maintain sliding window state.
   - Evaluated by **XGBoost Classifier** ($P_{\text{xgb}}$) and **Isolation Forest** ($S_{\text{if\_norm}}$).
   - Generates true local **SHAP TreeExplainer** factor attributions and a natural-language summary.
6. **9 Financial & Risk KPI Cards**:
   - Total Transactions Analyzed
   - Total Debits (Withdrawals)
   - Total Credits (Deposits)
   - Highest Transaction Amount (financial ranking)
   - Lowest Transaction Amount (financial ranking)
   - Average Transaction Amount (financial ranking)
   - Low-Risk Normal Count (risk ranking)
   - Medium-Risk Warning Count (risk ranking)
   - High-Risk Critical Anomaly Count (risk ranking)
7. **Strict Separation of Financial Amount vs. Risk Score**:
   - *Financial Ranking*: Highest Transaction Amount ($₹$) vs. Lowest Transaction Amount ($₹$).
   - *Risk Ranking*: 🔴 Highest Risk Transactions (Scores near $1.0$) vs. 🟡 Medium Risk vs. 🟢 Lowest Risk.
8. **Monthly Spending & Risk Insights (`/insights`)**:
   - Spending vs Risk comparative overview cards.
   - 30-Day dual-axis spending and risk trend chart.
   - Category breakdown table displaying transactions, expenditure, high-risk count, and risk posture.
9. **Transaction Deep Dive Inspector (`/transaction/{id}`)**:
   - Dual-model score gauge and decision boundary indicator.
   - Complete grid inspecting all 23 engineered features.
   - Horizontal SHAP waterfall bar chart with plain-English explanation.
   - Raw evaluated JSON payload viewer with one-click clipboard copying.
10. **Report Export Facilities**: Export the complete risk-analyzed statement to downloadable `.csv` or `.xlsx` format with top-3 SHAP attributions included.

---

## 13. Live Stream Extension & Anomaly Alert System

FinStream AI seamlessly distinguishes between three distinct data sources across the interface:
- **`UPLOADED BANK STATEMENT`**: Historical monthly baseline.
- **`SIMULATED TRANSACTIONS`**: On-demand scenario generation from the demonstration control panel.
- **`LIVE TRANSACTION STREAM`**: Real-time streaming transaction feed driven by the live engine.

### 13.1 Live Stream Controller & Alert Banner
1. **Live Mode Toggle**:
   - Header control button toggles between `● LIVE MODE` (active green pinging dot) and `○ PAUSED`.
   - In active mode, transactions are generated and evaluated every 2.5 seconds, updating charts, metrics, and tables in real time.
2. **Prominent High-Risk Anomaly Alert Banner**:
   - When any transaction exceeds the critical anomaly threshold ($S_{\text{risk}} \ge 0.70$), a high-contrast banner triggers immediately:
     $$\text{⚠ HIGH-RISK TRANSACTION DETECTED: [Tx ID | Amount | Risk Score | Timestamp]}$$
   - Includes an **"Investigate"** button navigating directly to `/transaction/{id}` for deep feature and SHAP inspection, along with a **"Dismiss"** control.
3. **Contextual Intelligence: Historical Baseline vs. Live Stream**:
   - Compares the uploaded 30-day statement baseline against real-time streaming transactions.
   - Displays:
     - Historical Average Amount & Average Risk Score
     - Live Stream Average Amount & Average Risk Score
     - Behavioral Risk Score Drift ($\Delta \text{Risk}$) and Amount Variance ($\Delta \text{Amount}\%$)
     - Behavioral status indicator (`Baseline Synchronized`, `Moderate Divergence`, or `Elevated Risk Drift`).

---

## 14. Project Completion Status & Roadmap

| Architectural Component | Milestone | Status | Details |
| :--- | :--- | :--- | :--- |
| **Phases 1–13 Core Engine** | Pipeline & Streaming | **COMPLETED** | 99/99 automated baseline tests passing |
| **Phase 14 Extension** | Bank Statement & Stream | **COMPLETED** | 9/9 new tests passing (108/108 total tests) |
| **Dual ML Inference** | XGBoost + Isolation Forest | **COMPLETED** | ROC-AUC: 0.9676, Artifacts in `models/artifacts/` |
| **Model Explainability** | SHAP TreeExplainer | **COMPLETED** | Top-5 directional local feature attributions |
| **Live Web Dashboards** | Zero-Install Web UI | **COMPLETED** | 4 responsive pages (`/`, `/statement`, `/insights`, `/transaction/{id}`) |
| **Transaction Simulator** | 4 Demo Scenarios + Custom | **COMPLETED** | Real ML pipeline execution |
| **Bank Statement Analyzer** | CSV & XLSX Local Engine | **COMPLETED** | Heuristic column mapping, cleaning audit, XLSX/CSV export |
| **Live Stream Alerts** | Real-Time Anomaly Engine | **COMPLETED** | Dynamic alert banner, investigate action, contextual comparison |
| **GitHub Preparation** | Git & `.gitignore` | **COMPLETED** | Clean ignore rules, ML artifacts tracked, 0 untracked leftovers |
| **Continuous Integration** | GitHub Actions CI | **COMPLETED** | Automated Python 3.12 test runner (`ci.yml`) |

---

## 15. License

This project is licensed under the [MIT License](LICENSE) — free for academic, educational, and commercial evaluation.
