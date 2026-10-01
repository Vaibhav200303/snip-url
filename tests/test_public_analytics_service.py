from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.config.settings import settings
from app.services.analytics_service import (
    AnalyticsRangeError,
    AnalyticsService,
    PublicAnalyticsNotFoundError,
)


def row(
    code: str,
    *,
    enabled: bool = True,
    expiration_at: datetime | None = None,
):
    return SimpleNamespace(
        short_code=code,
        is_enabled=enabled,
        expiration_at=expiration_at,
    )


class Urls:
    def __init__(self):
        self.by_code = {"abc": row("abc")}
        self.by_destination = {
            "https://example.com/": [row("abc"), row("xyz")],
        }
        self.destination_lookups = []

    def get_by_short_code(self, code):
        return self.by_code.get(code)

    def get_by_destination(self, destination):
        self.destination_lookups.append(destination)
        return self.by_destination.get(destination, [])


class Analytics:
    def daily_counts(self, code, start, end):
        clicks = 2 if code == "abc" else 3
        return [{"date": start, "clicks": clicks}]


def test_public_analytics_accepts_bare_and_full_short_url(monkeypatch):
    monkeypatch.setattr(settings, "public_base_url", "https://snip.example")
    service = AnalyticsService(Urls(), Analytics())
    start = end = date(2026, 10, 1)

    bare = service.get_public("abc", start, end)
    full = service.get_public("https://snip.example/abc", start, end)

    assert bare == full
    assert full["total_clicks"] == 2
    assert full["matched_links"] == 1


def test_public_analytics_aggregates_active_links_for_destination():
    urls = Urls()
    result = AnalyticsService(urls, Analytics()).get_public(
        "https://example.com", date(2026, 10, 1), date(2026, 10, 1)
    )

    assert urls.destination_lookups == ["https://example.com/"]
    assert result["matched_links"] == 2
    assert result["total_clicks"] == 5
    assert result["daily"] == [{"date": date(2026, 10, 1), "clicks": 5}]


@pytest.mark.parametrize(
    "candidate",
    [
        row("abc", enabled=False),
        row("abc", expiration_at=datetime.now(UTC) - timedelta(minutes=1)),
    ],
)
def test_public_analytics_hides_disabled_and_expired_links(candidate):
    urls = Urls()
    urls.by_code["abc"] = candidate

    with pytest.raises(PublicAnalyticsNotFoundError, match="no active link found"):
        AnalyticsService(urls, Analytics()).get_public(
            "abc", date(2026, 10, 1), date(2026, 10, 1)
        )


def test_public_analytics_rejects_invalid_input_neutrally():
    with pytest.raises(PublicAnalyticsNotFoundError, match="no active link found"):
        AnalyticsService(Urls(), Analytics()).get_public(
            "not a URL", date(2026, 10, 1), date(2026, 10, 1)
        )


def test_public_analytics_enforces_date_range():
    with pytest.raises(AnalyticsRangeError):
        AnalyticsService(Urls(), Analytics()).get_public(
            "abc", date(2026, 10, 2), date(2026, 10, 1)
        )
