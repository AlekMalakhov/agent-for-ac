"""Slack bot application."""

import asyncio
import logging

import sentry_sdk
import structlog
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

from src.config.settings import get_settings
from src.core.exceptions import SlackConnectionError
from src.core.logging import configure_logging
from src.services.jira import close_jira_service, get_jira_service
from src.slack.handlers import commands, events

logger = structlog.get_logger()

# Configure logging for slack_bolt and slack_sdk
# Use INFO level to avoid verbose ping-pong debug messages
logging.basicConfig(level=logging.INFO)
logging.getLogger("slack_bolt").setLevel(logging.INFO)
logging.getLogger("slack_sdk").setLevel(logging.INFO)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


def create_slack_app() -> tuple[AsyncApp, AsyncSocketModeHandler]:
    """
    Create Slack app and Socket Mode handler.

    Returns:
        tuple[AsyncApp, AsyncSocketModeHandler]: Slack app instance and Socket Mode handler.

    Raises:
        SlackConnectionError: If Slack app creation fails.
    """
    settings = get_settings()

    try:
        # Create Slack app with bot token
        app = AsyncApp(token=settings.slack_bot_token.get_secret_value())

        # Register command handlers
        commands.register(app)

        # Register event handlers for message interactions
        events.register(app)

        # Create Socket Mode handler with app-level token
        handler = AsyncSocketModeHandler(
            app, settings.slack_app_token.get_secret_value()
        )

        logger.info("slack_app_created")

        return app, handler
    except Exception as e:
        raise SlackConnectionError(f"Failed to create Slack app: {str(e)}") from e


async def startup() -> None:
    """
    Initialize all services on startup.

    Initializes logging, Sentry (if configured), and Jira service.
    Logs progress at each step.
    """
    # Initialize logging
    configure_logging()

    settings = get_settings()
    logger.info("slack_bot_starting", environment=settings.environment)

    # Initialize Sentry if configured
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=1.0 if settings.environment == "local" else 0.1,
        )
        logger.info("sentry_initialized")

    # Initialize Jira service
    try:
        await get_jira_service()
        logger.info("jira_service_initialized")
    except Exception as e:
        logger.warning(
            "jira_service_initialization_failed",
            error=str(e),
            note="Jira integration will not be available",
        )

    logger.info("slack_bot_startup_complete")


async def shutdown() -> None:
    """
    Clean up all services on shutdown.

    Closes Jira service connection.
    """
    logger.info("slack_bot_shutting_down")

    await close_jira_service()

    logger.info("slack_bot_shutdown")


async def main() -> None:
    """
    Main entry point for Slack bot.

    Orchestrates startup sequence, connects to Slack via Socket Mode,
    and handles graceful shutdown.
    """
    handler = None
    try:
        # Startup sequence
        await startup()

        # Create Slack app
        app, handler = create_slack_app()

        # Start Socket Mode - this is a blocking call that runs forever
        logger.info("connecting_to_slack")
        await handler.start_async()

        # Note: We never reach here because start_async() blocks
        # The "connected" log will appear in the socket mode handler's own logs

    except KeyboardInterrupt:
        logger.info("slack_bot_interrupted")
    except Exception as e:
        logger.error("slack_bot_failed", error=str(e), exc_info=True)
        raise
    finally:
        if handler:
            await handler.close_async()
        await shutdown()


if __name__ == "__main__":
    asyncio.run(main())
