# FinStream AI — React + TypeScript Intelligence Dashboard

A modern real-time financial transaction monitoring dashboard built with React, TypeScript, and Vite. Connects to the FinStream AI FastAPI backend via REST endpoints and real-time WebSocket streaming.

---

## Features

- **Live Streaming Ticker**: Real-time transaction and risk assessment feed over WebSockets (`/api/v1/ws/transactions`).
- **Dual-Model Anomaly Scoring**: Displays Supervised XGBoost probability and Unsupervised Isolation Forest normalized scores.
- **SHAP Local Feature Attributions**: Interactive horizontal feature contribution bars explaining the model's output.
- **Account Risk Inspector**: Low-latency risk profile lookup utilizing Redis hot-state caching with PostgreSQL fallback.
- **Audited Transaction History**: Paginated, filterable financial transaction event ledger.
- **Resilient WebSocket Client**: Automatic exponential backoff reconnection (1s..10s) with heartbeat ping-pong.
- **Infrastructure Health Grid**: Live status monitoring for FastAPI, PostgreSQL, Redis, and WebSocket connections.

---

## Setup & Execution

### 1. Install Dependencies
```bash
npm install
```

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/api/v1/ws/transactions
```

### 3. Run Development Server
```bash
npm run dev
```
The dashboard will be available at `http://localhost:5173`.

### 4. Build for Production
```bash
npm run build
```
Outputs static bundle to `dist/`.
