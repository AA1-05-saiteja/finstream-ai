"""
FinStream AI - Live Stream Engine & Contextual Comparison API
Drives real-time simulated live streaming transactions, maintains recent stream buffer,
triggers high-risk alerts, and computes contextual comparison against uploaded historical statements.
"""

from collections import deque
from datetime import datetime, timezone
import random
from typing import Any, Dict, List, Optional
from fastapi import APIRouter

from backend.routes.statement import get_latest_statement
from producer.account_profiles import AccountPool
from producer.scenario_generator import ScenarioGenerator
from streaming.pipeline_runner import EndToEndPipelineRunner

router = APIRouter(prefix="/stream", tags=["Live Transaction Stream"])

# Buffer for live streaming transactions (FIFO, max 50)
_live_stream_buffer = deque(maxlen=50)
_latest_high_risk_alert: Optional[Dict[str, Any]] = None

_stream_account_pool = AccountPool(size=30, seed=1337)
_stream_scenario_gen = ScenarioGenerator(account_pool=_stream_account_pool)
_stream_runner: Optional[EndToEndPipelineRunner] = None


def get_stream_runner() -> EndToEndPipelineRunner:
    """Returns singleton pipeline runner for stream operations."""
    global _stream_runner
    if _stream_runner is None:
        _stream_runner = EndToEndPipelineRunner()
    return _stream_runner


@router.post(
    "/tick",
    summary="Generate Live Stream Transaction",
    description="Emits a single live transaction event from the streaming pipeline, evaluates dual ML scores + SHAP, and broadcasts to WebSocket clients.",
)
def stream_tick(scenario: Optional[str] = None):
    """Generates a single live transaction in real time."""
    global _latest_high_risk_alert
    runner = get_stream_runner()

    # Probability mix for realistic live stream: 80% normal, 10% high amount, 7% velocity, 3% high risk
    if not scenario:
        roll = random.random()
        if roll < 0.78:
            tx = _stream_scenario_gen.generate_normal()
        elif roll < 0.88:
            tx = _stream_scenario_gen.generate_high_amount()
        elif roll < 0.95:
            burst = _stream_scenario_gen.generate_velocity_spike(count=4)
            tx = burst[-1]
        else:
            tx = _stream_scenario_gen.generate_high_amount()
            tx.amount = max(tx.amount, 180000.0)
            tx.device_id = f"DEV_LIVE_ANOMALY_{random.randint(100, 999)}"
            tx.scenario_label = "HIGH_RISK_LIVE"
    elif scenario == "high_risk":
        tx = _stream_scenario_gen.generate_high_amount()
        tx.amount = max(tx.amount, 195000.0)
        tx.device_id = f"DEV_ALERT_{random.randint(100, 999)}"
        tx.scenario_label = "HIGH_RISK_ALERT"
    elif scenario == "high_amount":
        tx = _stream_scenario_gen.generate_high_amount()
    elif scenario == "velocity_spike":
        burst = _stream_scenario_gen.generate_velocity_spike(count=4)
        tx = burst[-1]
    else:
        tx = _stream_scenario_gen.generate_normal()

    tx_dict = tx.to_clean_dict()
    # Unique live transaction ID
    import time
    tx_dict["transaction_id"] = f"LIVE_{int(time.time()*1000)%1000000:06d}"
    tx_dict["source"] = "LIVE_STREAM"

    result = runner.process_single_transaction(tx_dict, explain=True)
    rec = result["record"]

    live_entry = {
        "transaction_id": rec.get("transaction_id"),
        "account_id": rec.get("account_id"),
        "amount": float(rec.get("amount", 0.0)),
        "currency": "INR",
        "merchant_category": rec.get("merchant_category"),
        "city": rec.get("city"),
        "channel": rec.get("channel"),
        "timestamp": rec.get("timestamp"),
        "hybrid_risk_score": round(float(rec.get("hybrid_risk_score", 0.0)), 4),
        "risk_level": str(rec.get("risk_level", "LOW")),
        "xgboost_probability": round(float(rec.get("xgboost_probability", 0.0)), 4),
        "isolation_forest_normalized": round(float(rec.get("isolation_forest_normalized", 0.0)), 4),
        "top_shap_features": rec.get("top_shap_features", []),
        "source": "LIVE_STREAM",
    }

    _live_stream_buffer.append(live_entry)

    # Check for High Risk alert
    if live_entry["risk_level"] == "HIGH":
        _latest_high_risk_alert = {
            "transaction_id": live_entry["transaction_id"],
            "amount": live_entry["amount"],
            "risk_score": live_entry["hybrid_risk_score"],
            "account_id": live_entry["account_id"],
            "timestamp": live_entry["timestamp"],
            "alert_time": datetime.now(timezone.utc).isoformat(),
        }

    return live_entry


@router.get(
    "/events",
    summary="Get Recent Live Stream Events",
    description="Returns the buffer of recent live streaming transactions.",
)
def get_live_events():
    """Returns recent live stream transactions."""
    return list(_live_stream_buffer)


@router.get(
    "/comparison",
    summary="Contextual Statement vs. Live Stream Comparison",
    description="Compares baseline transaction intelligence from the uploaded historical statement against the real-time live stream.",
)
def get_stream_comparison():
    """Computes comparison between historical statement baseline and live stream."""
    stmt = get_latest_statement()
    stmt_summary = stmt.get("summary", {}) if stmt else {}

    live_events = list(_live_stream_buffer)
    stream_count = len(live_events)
    stream_avg_amt = round(sum(e["amount"] for e in live_events) / stream_count, 2) if stream_count > 0 else 0.0
    stream_avg_risk = round(sum(e["hybrid_risk_score"] for e in live_events) / stream_count, 4) if stream_count > 0 else 0.0

    return {
        "statement_loaded": bool(stmt and stmt.get("transactions")),
        "statement_filename": stmt.get("filename", "No Statement Uploaded") if stmt else "No Statement Uploaded",
        "historical_avg_amount": stmt_summary.get("average_transaction", 0.0),
        "historical_avg_risk": stmt_summary.get("avg_risk_score", 0.0),
        "historical_total_tx": stmt_summary.get("total_transactions", 0),
        "stream_count": stream_count,
        "stream_avg_amount": stream_avg_amt,
        "stream_avg_risk": stream_avg_risk,
        "latest_alert": _latest_high_risk_alert,
    }


@router.post(
    "/clear-alert",
    summary="Dismiss Latest High-Risk Alert",
)
def clear_alert():
    """Dismisses active high risk alert banner."""
    global _latest_high_risk_alert
    _latest_high_risk_alert = None
    return {"status": "cleared"}
