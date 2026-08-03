"""Utility for network connectivity and cloud endpoint health checking with caching."""

import logging
import time
import urllib.request
import urllib.error
from typing import Optional

from campus_helpdesk.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class ConnectivityChecker:
    """Checks internet connectivity and cloud API endpoint reachability with short TTL caching."""

    def __init__(
        self,
        check_url: str = "https://1.1.1.1",
        timeout_seconds: float = 1.5,
        cache_ttl_seconds: float = 15.0,
        settings: Optional[Settings] = None,
    ) -> None:
        if settings is not None:
            self.check_url = settings.connectivity_check_url
            self.timeout_seconds = settings.connectivity_check_timeout_seconds
            self.cache_ttl_seconds = settings.connectivity_check_cache_seconds
        else:
            self.check_url = check_url
            self.timeout_seconds = timeout_seconds
            self.cache_ttl_seconds = cache_ttl_seconds

        # Cache variables for internet connectivity
        self._last_online_check_time: float = 0.0
        self._last_online_result: bool = False

        # Cache variables for cloud endpoint reachability
        self._last_endpoint_check_time: float = 0.0
        self._last_endpoint_result: bool = False
        self._last_endpoint_url: str = ""

    def is_online(self, force_recheck: bool = False) -> bool:
        """Check whether internet connectivity is available, using cached results if valid.

        Args:
            force_recheck: If True, bypasses the cache and runs a fresh network check.

        Returns:
            True if public endpoint responds within timeout, False otherwise.
        """
        now = time.monotonic()
        if not force_recheck and (now - self._last_online_check_time) < self.cache_ttl_seconds:
            logger.debug(f"Using cached online status: {self._last_online_result}")
            return self._last_online_result

        result = self._ping_url(self.check_url, self.timeout_seconds)
        self._last_online_check_time = now
        self._last_online_result = result
        logger.debug(f"Fresh internet connectivity check ({self.check_url}): {result}")
        return result

    def is_cloud_endpoint_reachable(
        self,
        endpoint_url: str | None = None,
        force_recheck: bool = False,
    ) -> bool:
        """Check whether a specific cloud LLM API endpoint is reachable.

        Args:
            endpoint_url: The cloud API URL to ping. If empty or None, returns False.
            force_recheck: If True, bypasses the cache and performs a fresh check.

        Returns:
            True if the endpoint responds or accepts socket connection, False otherwise.
        """
        if not endpoint_url or not endpoint_url.strip():
            return False

        target_url = endpoint_url.strip()
        now = time.monotonic()

        if (
            not force_recheck
            and self._last_endpoint_url == target_url
            and (now - self._last_endpoint_check_time) < self.cache_ttl_seconds
        ):
            logger.debug(f"Using cached cloud endpoint status for {target_url}: {self._last_endpoint_result}")
            return self._last_endpoint_result

        result = self._ping_url(target_url, self.timeout_seconds)
        self._last_endpoint_check_time = now
        self._last_endpoint_result = result
        self._last_endpoint_url = target_url
        logger.debug(f"Fresh cloud endpoint reachability check ({target_url}): {result}")
        return result

    def _ping_url(self, url: str, timeout: float) -> bool:
        """Perform a lightweight HEAD or GET HTTP request to test connectivity."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CampusHelpdeskConnectivityChecker/1.0"},
                method="HEAD",
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status < 500
        except urllib.error.HTTPError as e:
            # 4xx or 3xx responses indicate network & server are reachable
            return e.code < 500
        except (urllib.error.URLError, TimeoutError, OSError, Exception) as err:
            logger.debug(f"Ping failed for {url}: {err}")
            return False
