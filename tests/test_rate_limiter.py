"""Unit tests for Rate Limiting and Brute Force Defense."""

from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException, Request
from keyforge.server.rate_limiter import SlidingWindowRateLimiter


def test_rate_limiter_allows_under_limit():
    limiter = SlidingWindowRateLimiter()
    mock_request = MagicMock(spec=Request)
    mock_request.client.host = "192.168.1.100"
    mock_request.headers.get.return_value = None

    for _ in range(5):
        limiter.check_rate_limit(mock_request, action="test_action", max_requests_per_minute=10)


def test_rate_limiter_blocks_over_limit():
    limiter = SlidingWindowRateLimiter()
    mock_request = MagicMock(spec=Request)
    mock_request.client.host = "192.168.1.200"
    mock_request.headers.get.return_value = None

    # First 3 should pass
    for _ in range(3):
        limiter.check_rate_limit(mock_request, action="strict_action", max_requests_per_minute=3)

    # 4th should raise HTTP 429
    with pytest.raises(HTTPException) as exc_info:
        limiter.check_rate_limit(mock_request, action="strict_action", max_requests_per_minute=3)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers
