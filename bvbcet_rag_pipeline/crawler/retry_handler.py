"""Retry Handler module for HTTP request retries with exponential backoff."""

import time
from typing import Callable, TypeVar

T = TypeVar("T")


class RetryHandler:
    """Executes callables with automatic exponential backoff retries."""

    @staticmethod
    def execute_with_retry(
        func: Callable[[], T],
        max_retries: int = 3,
        backoff_base: float = 1.5,
    ) -> T | None:
        """Execute callable with exponential backoff on exception."""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception:
                if attempt == max_retries - 1:
                    raise
                sleep_time = backoff_base ** (attempt + 1)
                time.sleep(sleep_time)
        return None
