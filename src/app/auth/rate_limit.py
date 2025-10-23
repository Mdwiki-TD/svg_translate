"""Simple in-memory rate limiting for authentication endpoints."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Deque, Dict


class RateLimiter:
    """Track request timestamps per key and enforce a maximum rate."""

    def __init__(self, limit: int, period: timedelta) -> None:
        self._limit = limit
        self._period = period
        self._hits: Dict[str, Deque[datetime]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """Return True if the key is allowed to proceed, False when throttled."""

        now = datetime.now(timezone.utc)
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > self._period:
                hits.popleft()
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True

    def try_after(self, key: str) -> timedelta:
        """Return the time until the key is allowed to proceed."""

        now = datetime.now(timezone.utc)
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > self._period:
                hits.popleft()
            if len(hits) >= self._limit:
                time_left = self._period - (now - hits[0])
                return time_left
            return timedelta(0)


login_rate_limiter = RateLimiter(limit=5, period=timedelta(minutes=1))
callback_rate_limiter = RateLimiter(limit=10, period=timedelta(minutes=1))
