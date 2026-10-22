"""
FinStream AI - FastAPI Application Entrypoint
Exposes real-time transaction intelligence, dual-model anomaly risk assessments, and SHAP explainability.
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.exceptions import register_exception_handlers
from backend.routes import (
    accounts_router,
    health_router,
    risks_router,
    transactions_router,
    websocket_router,
)
from config import get_settings

logger = logging.getLogger("backend_main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown event lifecycle."""
    settings = get_settings()
    logger.info("FinStream AI FastAPI backend starting up...")
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("Configured CORS Origins: %s", settings.cors_origins_list)
    yield
    logger.info("FinStream AI FastAPI backend shutting down...")


def create_app() -> FastAPI:
    """Factory creating and configuring the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="FinStream AI — Transaction Intelligence API",
        description=(
            "Decision-support REST API for real-time financial transaction risk scoring, "
            "dual-model anomaly detection (XGBoost + Isolation Forest), and local SHAP explainability."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Configure CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register Global Exception Handlers
    register_exception_handlers(app)

    # 3. Register API Version 1 Routers
    api_v1_prefix = "/api/v1"
    app.include_router(health_router, prefix=api_v1_prefix)
    app.include_router(transactions_router, prefix=api_v1_prefix)
    app.include_router(risks_router, prefix=api_v1_prefix)
    app.include_router(accounts_router, prefix=api_v1_prefix)
    app.include_router(websocket_router, prefix=api_v1_prefix)

    # 4. Mount Static Assets & Serve Live Interactive Dashboard
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def root():
        """Serves the FinStream AI live web dashboard."""
        html_file = Path(__file__).parent / "static" / "index.html"
        if html_file.exists():
            return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>FinStream AI Dashboard Loading...</h1>")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
    )
