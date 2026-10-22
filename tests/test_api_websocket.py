"""
Unit tests for WebSocket real-time streaming routes and connection manager.
"""

import asyncio
from fastapi.testclient import TestClient
import pytest

from backend.event_service import EventService
from backend.main import create_app
from backend.websocket_manager import WebSocketManager


@pytest.fixture
def app_with_fresh_ws():
    """Provides a TestClient with a fresh isolated WebSocketManager."""
    ws_mgr = WebSocketManager()
    event_svc = EventService(ws_manager=ws_mgr)
    app = create_app()

    # Override singleton dependency
    from backend.websocket_manager import get_ws_manager
    from backend.event_service import get_event_service
    import backend.routes.websocket as ws_route_mod

    # Patch route manager
    original_get_mgr = ws_route_mod.get_ws_manager
    ws_route_mod.get_ws_manager = lambda: ws_mgr

    client = TestClient(app)
    yield client, ws_mgr, event_svc
    ws_route_mod.get_ws_manager = original_get_mgr


def test_websocket_connection_and_handshake(app_with_fresh_ws):
    client, ws_mgr, _ = app_with_fresh_ws

    with client.websocket_connect("/api/v1/ws/transactions") as websocket:
        data = websocket.receive_json()
        assert data["event"] == "connection_established"
        assert data["version"] == "1.0"
        assert "message" in data["data"]
        assert ws_mgr.active_count == 1

    # After exiting context, client should be disconnected
    assert ws_mgr.active_count == 0


def test_websocket_ping_pong_heartbeat(app_with_fresh_ws):
    client, ws_mgr, _ = app_with_fresh_ws

    with client.websocket_connect("/api/v1/ws/transactions") as websocket:
        # Read handshake
        _ = websocket.receive_json()

        # Send ping
        websocket.send_text("ping")
        response = websocket.receive_text()
        assert response == "pong"


def test_websocket_broadcast_risk_assessed_event(app_with_fresh_ws):
    client, ws_mgr, event_svc = app_with_fresh_ws

    with client.websocket_connect("/api/v1/ws/transactions") as websocket:
        # Read handshake
        _ = websocket.receive_json()

        # Broadcast event
        sample_eval = {
            "transaction_id": "TX_WS_001",
            "account_id": "ACC_WS_99",
            "amount": 99999.0,
            "currency": "INR",
            "hybrid_risk_score": 0.895,
            "risk_level": "HIGH",
            "xgboost_probability": 0.95,
            "isolation_forest_normalized": 0.80,
            "top_shap_features": [
                {
                    "feature": "amount",
                    "feature_value": 99999.0,
                    "shap_value": 1.45,
                    "direction": "increases_anomaly",
                    "rank": 1,
                }
            ],
        }

        # Run async broadcast
        delivered = asyncio.run(event_svc.broadcast_risk_assessed(sample_eval))
        assert delivered == 1

        # Receive streamed event on client
        msg = websocket.receive_json()
        assert msg["event"] == "transaction_risk_assessed"
        assert msg["data"]["transaction_id"] == "TX_WS_001"
        assert msg["data"]["risk_level"] == "HIGH"
        assert msg["data"]["hybrid_risk_score"] == 0.895
        assert len(msg["data"]["top_shap_features"]) == 1
