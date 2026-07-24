"""Logging configuration for the backend with rotating daily file handler."""

import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def configure_logging(log_level: str) -> None:
    """Configure process-wide console and daily rotating file logging."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger()
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if re-configured
    if logger.handlers:
        return

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    # 1. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Daily Rotating File Handler under logs/
    logs_dir = Path("logs")
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_file = logs_dir / f"{today_str}.log"

        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as err:
        logger.warning(f"Could not initialize rotating log file handler: {err}")

