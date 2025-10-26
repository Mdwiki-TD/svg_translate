"""Unit tests for in-memory rate limiter."""
import time
from datetime import timedelta

from src.app.app_routes.auth.rate_limit import RateLimiter


def test_rate_limiter_allow_and_try_after():
    rl = RateLimiter(limit=2, period=timedelta(seconds=0.2))
    key = "client-ip"
    assert rl.allow(key) is True
    assert rl.allow(key) is True
    # Third hit within window should be throttled
    assert rl.allow(key) is False
    wait = rl.try_after(key)
    assert wait.total_seconds() > 0
    # After the period passes, it's allowed again
    time.sleep(0.25)
    assert rl.allow(key) is True