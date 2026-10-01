from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.redirect_service import (
    RedirectService,
    UrlDisabledError,
    UrlExpiredError,
    UrlNotFoundError,
)


class Cache:
    def __init__(self, value=None):
        self.value = value
        self.set_calls = []

    def get(self, _code):
        return self.value

    def set(self, *args):
        self.set_calls.append(args)


class Repository:
    def __init__(self, row):
        self.row = row

    def get_by_short_code(self, _code):
        return self.row


def test_cache_hit_avoids_repository():
    service = RedirectService(Repository(None), Cache("https://cached.example"))
    assert service.get_long_url("code") == "https://cached.example"


def test_missing_url_raises():
    with pytest.raises(UrlNotFoundError):
        RedirectService(Repository(None), Cache()).get_long_url("missing")


def test_disabled_url_raises():
    row = SimpleNamespace(is_enabled=False, expiration_at=None, long_url="https://x")
    with pytest.raises(UrlDisabledError):
        RedirectService(Repository(row), Cache()).get_long_url("code")


def test_expired_url_raises():
    row = SimpleNamespace(
        is_enabled=True,
        expiration_at=datetime.now(UTC) - timedelta(seconds=1),
        long_url="https://x",
    )
    with pytest.raises(UrlExpiredError):
        RedirectService(Repository(row), Cache()).get_long_url("code")
