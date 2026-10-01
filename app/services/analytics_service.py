from datetime import date

from app.config.settings import settings
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.url_repository import UrlRepository
from app.services.url_service import UrlNotFoundError


class AnalyticsRangeError(ValueError):
    pass


class AnalyticsService:
    def __init__(self, urls: UrlRepository, analytics: AnalyticsRepository):
        self.urls = urls
        self.analytics = analytics

    def get(self, short_code: str, start: date, end: date) -> dict:
        if self.urls.get_by_short_code(short_code) is None:
            raise UrlNotFoundError("short URL not found")
        days = (end - start).days + 1
        if days < 1 or days > settings.analytics_max_range_days:
            raise AnalyticsRangeError(
                f"date range must be between 1 and {settings.analytics_max_range_days} days"
            )
        daily = self.analytics.daily_counts(short_code, start, end)
        return {
            "short_code": short_code,
            "total_clicks": sum(item["clicks"] for item in daily),
            "daily": daily,
        }
