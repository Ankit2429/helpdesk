"""Logging configuration for the backend."""

import logging


def configure_logging(log_level: str) -> None:
    """Configure application logging once for the current process."""
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
