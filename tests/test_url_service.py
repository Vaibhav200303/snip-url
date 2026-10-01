from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.schemas.url import ShortenUrlRequest, UpdateUrlRequest
from app.services.url_service import (
    CodeGenerationError,
    CustomAliasAlreadyExistsError,
    UrlService,
)


class Generator:
    def __init__(self):
        self.value = 0

    def generate(self):
        self.value += 1
        return f"code{self.value}"


class Repository:
    def __init__(self, failures=0):
        self.failures = failures
        self.rows = {}

    def create(self, code, long_url, created_at, expiration_at, is_custom):
        if self.failures:
            self.failures -= 1
            return False
        if code in self.rows:
            return False
        self.rows[code] = SimpleNamespace(
            short_code=code,
            long_url=long_url,
            created_at=created_at,
            expiration_at=expiration_at,
            is_custom=is_custom,
            is_enabled=True,
        )
        return True

    def get_by_short_code(self, code):
        return self.rows.get(code)

    def update(self, row, long_url, expiration_at, enabled):
        row.long_url = long_url
        row.expiration_at = expiration_at
        row.is_enabled = enabled

    def delete(self, row):
        self.rows.pop(row.short_code)


class Cache:
    def __init__(self):
        self.deleted = []

    def delete(self, code):
        self.deleted.append(code)


def test_generated_code_retries_collisions():
    repository = Repository(failures=2)
    service = UrlService(repository, Generator(), Cache())
    result = service.shorten(ShortenUrlRequest(long_url="https://example.com"))
    assert result["short_code"] == "code3"


def test_custom_alias_conflict():
    repository = Repository(failures=1)
    service = UrlService(repository, Generator(), Cache())
    with pytest.raises(CustomAliasAlreadyExistsError):
        service.shorten(
            ShortenUrlRequest(long_url="https://example.com", custom_alias="mine")
        )


def test_generated_code_exhaustion(monkeypatch):
    monkeypatch.setattr("app.services.url_service.settings.generated_code_retries", 2)
    service = UrlService(Repository(failures=3), Generator(), Cache())
    with pytest.raises(CodeGenerationError):
        service.shorten(ShortenUrlRequest(long_url="https://example.com"))


def test_update_invalidates_cache():
    repository = Repository()
    cache = Cache()
    repository.create("mine", "https://old.example", datetime.now(UTC), None, True)
    service = UrlService(repository, Generator(), cache)
    result = service.update(
        "mine", UpdateUrlRequest(long_url="https://new.example", is_enabled=False)
    )
    assert result["long_url"] == "https://new.example/"
    assert result["is_enabled"] is False
    assert cache.deleted == ["mine"]
