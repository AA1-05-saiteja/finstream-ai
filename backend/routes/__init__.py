"""
FinStream AI - API Route Handlers
"""

from backend.routes.accounts import router as accounts_router
from backend.routes.health import router as health_router
from backend.routes.risks import router as risks_router
from backend.routes.transactions import router as transactions_router
from backend.routes.websocket import router as websocket_router

__all__ = [
    "health_router",
    "transactions_router",
    "risks_router",
    "accounts_router",
    "websocket_router",
]
