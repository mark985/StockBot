"""
Logging configuration using loguru.
Provides centralized logging setup for the entire application.
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import get_settings


def setup_logging():
    """
    Configure loguru logging for the application.

    Sets up:
    - Console output with color
    - File rotation with retention
    - Different log levels for console vs file
    """
    settings = get_settings()

    # Remove default handler
    logger.remove()

    # Console handler - INFO and above with color
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )

    # File handler - DEBUG and above, rotated daily
    log_file = settings.logs_dir / "stockbot_{time:YYYY-MM-DD}.log"
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",  # Rotate at midnight
        retention="30 days",  # Keep logs for 30 days
        compression="zip",  # Compress old logs
    )

    logger.info("Logging configured")
    logger.debug(f"Log file: {log_file}")

    return logger


def get_logger():
    """Get the configured logger instance."""
    return logger
