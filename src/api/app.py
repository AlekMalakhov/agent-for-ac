"""FastAPI application factory and lifespan management."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from slack_sdk.web.async_client import AsyncWebClient

from src.api.routes import health, webhooks
from src.core.logging import configure_logging

logger = structlog.get_logger()

# Check if running in serverless environment (Vercel)
IS_SERVERLESS = os.environ.get("VERCEL", "0") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for startup and shutdown.

    Initializes Slack client and Jira service for webhook processing.
    In serverless mode, initialization is deferred to request time.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control flow during application lifetime.
    """
    # Startup
    logger.info("fastapi_starting", serverless=IS_SERVERLESS)

    if not IS_SERVERLESS:
        # Only initialize eagerly in non-serverless environments
        from src.config.settings import get_settings
        from src.services.jira import get_jira_service

        try:
            settings = get_settings()
            app.state.slack_client = AsyncWebClient(
                token=settings.slack_bot_token.get_secret_value()
            )
            logger.info("slack_client_initialized")

            await get_jira_service()
            logger.info("jira_service_initialized")
        except Exception as e:
            logger.warning(
                "service_initialization_failed",
                error=str(e),
                note="Services will be initialized on first request",
            )

    logger.info("fastapi_started")

    yield

    # Shutdown
    logger.info("fastapi_shutting_down")
    if not IS_SERVERLESS:
        from src.services.jira import close_jira_service
        await close_jira_service()
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
    app.include_router(webhooks.router)

    return app
