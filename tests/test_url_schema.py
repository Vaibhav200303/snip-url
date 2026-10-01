from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.url import ShortenUrlRequest, UpdateUrlRequest


@pytest.mark.parametrize("alias", ["admin", "AdMiN", "api", "docs", "bad alias", "a!b"])
def test_rejects_reserved_or_unsafe_aliases(alias):
    with pytest.raises(ValidationError):
        ShortenUrlRequest(long_url="https://example.com", custom_alias=alias)


def test_rejects_expiration_in_the_past():
    with pytest.raises(ValidationError):
        ShortenUrlRequest(
            long_url="https://example.com",
            expiration_at=datetime.now(UTC) - timedelta(seconds=1),
        )


def test_update_requires_a_change():
    with pytest.raises(ValidationError):
        UpdateUrlRequest()


def test_update_cannot_set_and_clear_expiration():
    with pytest.raises(ValidationError):
        UpdateUrlRequest(
            expiration_at=datetime.now(UTC) + timedelta(days=1),
            clear_expiration=True,
        )
