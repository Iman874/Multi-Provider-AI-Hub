"""
Logging configuration for AI Generative Core.

Uses loguru for structured logging with support for JSON and text formats.
Call setup_logging() once during application startup.
"""

import sys

from loguru import logger


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format - "json" for structured or "text" for human-readable.
    """
    # Remove default loguru handler
    logger.remove()

    if log_format == "json":
        # JSON format for production / log aggregation
        logger.add(
            sys.stdout,
            level=log_level.upper(),
            format="{message}",
            serialize=True,
        )
    else:
        # Human-readable text format for development
        logger.add(
            sys.stdout,
            level=log_level.upper(),
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
        )

    logger.info(
        "Logging initialized",
        level=log_level,
        format=log_format,
    )
