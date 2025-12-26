"""FastAPI application factory and lifespan management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from src.api.routes import health
from src.core.logging import configure_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for startup and shutdown.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control flow during application lifetime.
    """
    # Startup
    logger.info("fastapi_starting")
    logger.info("fastapi_started")

    yield

    # Shutdown
    logger.info("fastapi_shutdown")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Initializes logging, creates the FastAPI app with lifespan management,
    and registers all route handlers.

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    # Initialize logging
    configure_logging()

    # Create app
    app = FastAPI(
        title="Agent for AC API",
        description="Health monitoring for Agent for AC",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(health.router)

    return app
