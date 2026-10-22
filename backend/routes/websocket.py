"""
FinStream AI - WebSocket Streaming Routes
Provides real-time event streaming of transactions and risk assessments.
"""

from datetime import datetime, timezone
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.websocket_manager import get_ws_manager

logger = logging.getLogger("websocket_route")

router = APIRouter(prefix="/ws", tags=["Real-Time Streaming"])


@router.websocket("/transactions")
async def websocket_transactions_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint streaming live transaction risk evaluation events to connected dashboard clients.
    Clients receive real-time JSON events on transaction arrival and anomaly risk computation.
    """
    ws_manager = get_ws_manager()
    await ws_manager.connect(websocket)

    # 1. Send initial connection confirmation handshake
    try:
        await websocket.send_json({
            "event": "connection_established",
            "version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "message": "Connected to FinStream AI Real-Time Transaction Intelligence Stream",
                "active_clients": ws_manager.active_count,
            },
        })
    except Exception as exc:
        logger.warning("Failed to send initial handshake to client: %s", exc)
        await ws_manager.disconnect(websocket)
        return

    # 2. Keepalive & Client Message Loop
    try:
        while True:
            # Await client heartbeat or message (e.g. ping)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            else:
                # Echo receipt or acknowledge
                logger.debug("Received message from WebSocket client: %s", data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected normally.")
    except Exception as exc:
        logger.warning("WebSocket client connection error: %s", exc)
        await ws_manager.disconnect(websocket)
