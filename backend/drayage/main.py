"""
Application entrypoint and FastAPI factory for Component 2: Intelligent Drayage Truck Optimization System.
Can run standalone or be mounted into the smart port management umbrella backend.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import check_database_connection
from .router import router as drayage_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("drayage.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown handler."""
    logger.info("Initializing Component 2 Drayage Optimization Backend...")
    db_ok = check_database_connection()
    if db_ok:
        logger.info("Successfully verified connection to PostgreSQL 'smart_port_management'.")
    else:
        logger.warning(
            "PostgreSQL database is currently not reachable or credentials not set. "
            "Backend will operate with fallback service layer."
        )
    yield
    logger.info("Shutting down Component 2 Drayage Optimization Backend.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Component 2: Intelligent Drayage Truck Optimization API",
        description=(
            "RESTful API service for terminal drayage truck optimization, driver task dispatch, "
            "GPS location telemetry, and lifecycle status tracking inside the port."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure CORS for Flutter mobile client and React web frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount router under Component 2 specific prefix and top-level v1 prefix
    app.include_router(drayage_router, prefix="/api/v1/drayage")
    app.include_router(drayage_router, prefix="/api/v1")

    @app.get("/", tags=["Root"])
    def root():
        return {
            "component": "Component 2: Intelligent Drayage Truck Optimization System",
            "status": "online",
            "docs_url": "/docs",
            "health_url": "/api/v1/health",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.drayage.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
