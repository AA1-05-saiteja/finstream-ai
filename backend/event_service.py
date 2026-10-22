"""
FinStream AI - Real-Time Event Publishing Service
Structures and broadcasts typed streaming events to connected WebSocket clients.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.websocket_manager import WebSocketManager, get_ws_manager

logger = logging.getLogger("event_service")


class TransactionRiskEventData(BaseModel):
    """Payload data for a transaction risk assessment streaming event."""

    transaction_id: str
    account_id: str
    amount: float
    currency: str = "INR"
    merchant_category: Optional[str] = None
    city: Optional[str] = None
    channel: Optional[str] = None
    hybrid_risk_score: float
    risk_level: str
    xgboost_probability: float
    isolation_forest_normalized: float
    top_shap_features: Optional[List[Dict[str, Any]]] = None


class StreamEvent(BaseModel):
    """Versioned outer event envelope for all WebSocket messages."""

    event: str = Field(..., description="Event classification type")
    version: str = Field(default="1.0", description="Event schema version")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Event dispatch timestamp (ISO 8601 UTC)",
    )
    data: Dict[str, Any] = Field(..., description="Event payload dictionary")


class EventService:
    """
    Service responsible for constructing typed streaming events and broadcasting via WebSocketManager.
    Guarantees non-blocking execution so WebSocket failures never interrupt database durability.
    """

    def __init__(self, ws_manager: Optional[WebSocketManager] = None):
        self.ws_manager = ws_manager or get_ws_manager()

    async def broadcast_risk_assessed(
        self,
        evaluation_record: Dict[str, Any],
    ) -> int:
        """
        Builds and broadcasts a `transaction_risk_assessed` event to all connected clients.
        Returns the number of clients that received the event.
        """
        try:
            event_data = {
                "transaction_id": str(evaluation_record.get("transaction_id", "")),
                "account_id": str(evaluation_record.get("account_id", "")),
                "amount": float(evaluation_record.get("amount", 0.0)),
                "currency": str(evaluation_record.get("currency", "INR")),
                "merchant_category": evaluation_record.get("merchant_category"),
                "city": evaluation_record.get("city"),
                "channel": evaluation_record.get("channel"),
                "hybrid_risk_score": round(float(evaluation_record.get("hybrid_risk_score", 0.0)), 4),
                "risk_level": str(evaluation_record.get("risk_level", "LOW")),
                "xgboost_probability": round(float(evaluation_record.get("xgboost_probability", 0.0)), 4),
                "isolation_forest_normalized": round(float(evaluation_record.get("isolation_forest_normalized", 0.0)), 4),
                "top_shap_features": evaluation_record.get("top_shap_features", []),
            }

            event = StreamEvent(
                event="transaction_risk_assessed",
                version="1.0",
                data=event_data,
            )

            delivered_count = await self.ws_manager.broadcast(event.model_dump())
            logger.debug(
                "Broadcasted transaction_risk_assessed event for %s to %d clients",
                event_data["transaction_id"],
                delivered_count,
            )
            return delivered_count
        except Exception as exc:
            logger.warning("Event broadcasting encountered an error: %s", exc)
            return 0


_default_event_service: Optional[EventService] = None


def get_event_service() -> EventService:
    """Returns singleton EventService instance."""
    global _default_event_service
    if _default_event_service is None:
        _default_event_service = EventService()
    return _default_event_service
