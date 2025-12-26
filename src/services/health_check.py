"""Health check service."""

import structlog

logger = structlog.get_logger()


async def check_health() -> dict[str, str]:
    """
    Check application health.

    Returns basic health status. Can be extended to check
    external services (Jira, Slack) if needed.

    Returns:
        dict: Health status information.
    """
    return {
        "status": "healthy",
        "service": "agent-for-ac",
    }
