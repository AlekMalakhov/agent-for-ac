"""Structured logging configuration using structlog."""

import sys

import structlog

from src.config.settings import get_settings


def configure_logging() -> None:
    """
    Configure structured logging with structlog.

    Configures structlog with appropriate processors and renderers based on the
    execution environment:
    - TTY (development): Pretty console output with colors
    - Non-TTY (production): JSON structured logs

    Log level is determined by the application settings.
    """
    settings = get_settings()

    # Determine if running in TTY (for pretty console output)
    is_tty = sys.stderr.isatty()

    # Choose renderer based on TTY
    if is_tty:
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(settings.log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
