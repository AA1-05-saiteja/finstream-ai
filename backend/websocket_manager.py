"""
FinStream AI - WebSocket Connection Manager
Tracks active client connections and provides safe broadcast event delivery.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("websocket_manager")


class WebSocketManager:
    """
    Manages active WebSocket connections for real-time transaction and risk streaming.
    Handles concurrent client broadcasting, graceful disconnections, and error isolation.
    """

    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        """Returns number of currently active WebSocket client connections."""
        return len(self._active_connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts and registers a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._active_connections.add(websocket)
        logger.info("WebSocket client connected. Total active clients: %d", len(self._active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Removes a disconnected WebSocket client."""
        async with self._lock:
            if websocket in self._active_connections:
                self._active_connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total active clients: %d", len(self._active_connections))

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> bool:
        """Sends a JSON message to a single specific client."""
        try:
            await websocket.send_json(message)
            return True
        except Exception as exc:
            logger.warning("Failed to send message to client: %s", exc)
            await self.disconnect(websocket)
            return False

    async def broadcast(self, message: Dict[str, Any]) -> int:
        """
        Broadcasts a JSON message to all connected clients.
        Dead connections are automatically pruned without raising exceptions.
        Returns the count of successfully notified clients.
        """
        if not self._active_connections:
            return 0

        async with self._lock:
            clients_snapshot = list(self._active_connections)

        dead_clients: List[WebSocket] = []
        sent_count = 0

        for client in clients_snapshot:
            try:
                await client.send_json(message)
                sent_count += 1
            except (WebSocketDisconnect, RuntimeError, Exception) as exc:
                logger.debug("Client broadcast failed (client disconnected): %s", exc)
                dead_clients.append(client)

        if dead_clients:
            async with self._lock:
                for dead in dead_clients:
                    if dead in self._active_connections:
                        self._active_connections.remove(dead)
            logger.info("Pruned %d dead WebSocket connections. Remaining: %d", len(dead_clients), len(self._active_connections))

        return sent_count


_default_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """Returns singleton WebSocketManager instance."""
    global _default_ws_manager
    if _default_ws_manager is None:
        _default_ws_manager = WebSocketManager()
    return _default_ws_manager
