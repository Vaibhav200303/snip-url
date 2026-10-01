from datetime import date, timedelta

import pytest

from app.services.analytics_service import AnalyticsRangeError, AnalyticsService
from app.services.url_service import UrlNotFoundError


class Urls:
    def __init__(self, exists=True):
        self.exists = exists

    def get_by_short_code(self, _code):
        return object() if self.exists else None


class Analytics:
    def daily_counts(self, _code, start, end):
        return [{"date": start, "clicks": 2}, {"date": end, "clicks": 3}]


def test_analytics_totals_daily_counts():
    result = AnalyticsService(Urls(), Analytics()).get(
        "code", date(2026, 1, 1), date(2026, 1, 2)
    )
    assert result["total_clicks"] == 5


def test_analytics_rejects_missing_url():
    with pytest.raises(UrlNotFoundError):
        AnalyticsService(Urls(False), Analytics()).get(
            "code", date(2026, 1, 1), date(2026, 1, 2)
        )


def test_analytics_rejects_excessive_range():
    with pytest.raises(AnalyticsRangeError):
        AnalyticsService(Urls(), Analytics()).get(
            "code", date(2025, 1, 1), date(2025, 1, 1) + timedelta(days=366)
        )
