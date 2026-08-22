"""Sliding-Window Rate Limiter for Abuse and Brute-Force Prevention."""

from __future__ import annotations

import time
from collections import defaultdict
from fastapi import HTTPException, Request, status

from keyforge.server.config import settings


class SlidingWindowRateLimiter:
    """In-memory sliding-window log rate limiter keyed by client IP and action route."""

    def __init__(self) -> None:
        # dict of key -> list of timestamps
        self._history: dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(
        self,
        request: Request,
        action: str = "default",
        max_requests_per_minute: int = 60,
    ) -> None:
        """Evaluate if the client request exceeds the allowed rate limit."""
        if not settings.rate_limit_enabled:
            return

        client_ip = request.client.host if request.client else "127.0.0.1"
        # Extract X-Forwarded-For if behind reverse proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        key = f"{client_ip}:{action}"
        now = time.time()
        window_start = now - 60.0

        # Purge entries older than 60 seconds
        timestamps = [ts for ts in self._history[key] if ts > window_start]
        if len(timestamps) >= max_requests_per_minute:
            retry_after = int(60 - (now - timestamps[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for action '{action}'. Retry after {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)
        self._history[key] = timestamps


limiter = SlidingWindowRateLimiter()
