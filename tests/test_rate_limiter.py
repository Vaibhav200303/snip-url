import pytest
from redis import RedisError

from app.services.rate_limiter import RateLimiter, RateLimitExceededError


def test_rate_limiter_uses_atomic_fixed_window(monkeypatch):
    calls = []

    def evaluate(script, keys, key, window):
        calls.append((script, keys, key, window))
        return 2

    monkeypatch.setattr("app.services.rate_limiter.redis_client.eval", evaluate)
    RateLimiter().check("create", "203.0.113.1", 2, 60)
    assert calls[0][1:] == (1, "rate:create:203.0.113.1", 60)
    assert "count == 1" in calls[0][0]


def test_rate_limiter_rejects_over_limit(monkeypatch):
    monkeypatch.setattr("app.services.rate_limiter.redis_client.eval", lambda *_: 3)
    with pytest.raises(RateLimitExceededError):
        RateLimiter().check("create", "203.0.113.1", 2, 60)


def test_rate_limiter_fails_open_on_redis_error(monkeypatch):
    def fail(*_args):
        raise RedisError("unavailable")

    monkeypatch.setattr("app.services.rate_limiter.redis_client.eval", fail)
    RateLimiter().check("create", "203.0.113.1", 2, 60)
