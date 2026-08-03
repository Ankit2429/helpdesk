"""Unit tests for ConnectivityChecker online status and cloud endpoint reachability caching."""

from unittest.mock import MagicMock, patch
import pytest

from campus_helpdesk.infrastructure.llm.connectivity_checker import ConnectivityChecker
from campus_helpdesk.config.settings import Settings


def test_is_online_success():
    """Verify is_online returns True when endpoint ping succeeds."""
    checker = ConnectivityChecker(check_url="https://1.1.1.1", timeout_seconds=1.5, cache_ttl_seconds=15.0)

    with patch.object(checker, "_ping_url", return_value=True) as mock_ping:
        result = checker.is_online()
        assert result is True
        mock_ping.assert_called_once_with("https://1.1.1.1", 1.5)


def test_is_online_failure():
    """Verify is_online returns False when endpoint ping fails/times out."""
    checker = ConnectivityChecker(check_url="https://1.1.1.1", timeout_seconds=1.5, cache_ttl_seconds=15.0)

    with patch.object(checker, "_ping_url", return_value=False) as mock_ping:
        result = checker.is_online()
        assert result is False
        mock_ping.assert_called_once_with("https://1.1.1.1", 1.5)


def test_is_online_caching_behavior():
    """Verify repeated calls within TTL window use cached result without additional network requests."""
    checker = ConnectivityChecker(check_url="https://1.1.1.1", cache_ttl_seconds=15.0)

    with patch.object(checker, "_ping_url", return_value=True) as mock_ping:
        # First call: performs fresh ping
        res1 = checker.is_online()
        assert res1 is True
        assert mock_ping.call_count == 1

        # Second call immediately: must use cache, mock_ping count remains 1
        res2 = checker.is_online()
        assert res2 is True
        assert mock_ping.call_count == 1

        # Third call with force_recheck=True: bypasses cache
        res3 = checker.is_online(force_recheck=True)
        assert res3 is True
        assert mock_ping.call_count == 2


def test_is_cloud_endpoint_reachable_caching():
    """Verify is_cloud_endpoint_reachable checks endpoint and caches results per endpoint URL."""
    checker = ConnectivityChecker(cache_ttl_seconds=15.0)
    cloud_url = "https://api.cloud-llm.example.com/v1"

    with patch.object(checker, "_ping_url", return_value=True) as mock_ping:
        # Empty endpoint returns False immediately
        assert checker.is_cloud_endpoint_reachable(None) is False
        assert checker.is_cloud_endpoint_reachable("") is False
        assert mock_ping.call_count == 0

        # First valid call
        res1 = checker.is_cloud_endpoint_reachable(cloud_url)
        assert res1 is True
        assert mock_ping.call_count == 1

        # Second call uses cache
        res2 = checker.is_cloud_endpoint_reachable(cloud_url)
        assert res2 is True
        assert mock_ping.call_count == 1

        # Forced recheck calls mock_ping again
        res3 = checker.is_cloud_endpoint_reachable(cloud_url, force_recheck=True)
        assert res3 is True
        assert mock_ping.call_count == 2


def test_connectivity_checker_with_settings():
    """Verify ConnectivityChecker initializes correctly from application Settings."""
    settings = Settings(
        connectivity_check_url="https://custom-health.endpoint.com",
        connectivity_check_timeout_seconds=2.5,
        connectivity_check_cache_seconds=30.0,
    )
    checker = ConnectivityChecker(settings=settings)

    assert checker.check_url == "https://custom-health.endpoint.com"
    assert checker.timeout_seconds == 2.5
    assert checker.cache_ttl_seconds == 30.0
