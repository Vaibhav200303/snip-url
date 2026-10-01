from datetime import UTC, date, datetime, timedelta
from urllib.parse import unquote, urlsplit

from pydantic import HttpUrl, TypeAdapter, ValidationError

from app.config.settings import settings
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.url_repository import UrlRepository
from app.schemas.url import ALIAS_PATTERN
from app.services.url_service import UrlNotFoundError


class AnalyticsRangeError(ValueError):
    pass


class PublicAnalyticsNotFoundError(Exception):
    pass


class AnalyticsService:
    def __init__(self, urls: UrlRepository, analytics: AnalyticsRepository):
        self.urls = urls
        self.analytics = analytics

    def get(self, short_code: str, start: date, end: date) -> dict:
        if self.urls.get_by_short_code(short_code) is None:
            raise UrlNotFoundError("short URL not found")
        self._validate_range(start, end)
        daily = self.analytics.daily_counts(short_code, start, end)
        return {
            "short_code": short_code,
            "total_clicks": sum(item["clicks"] for item in daily),
            "daily": daily,
        }

    def get_public(
        self,
        value: str,
        start: date | None = None,
        end: date | None = None,
    ) -> dict:
        end = end or datetime.now(UTC).date()
        start = start or end - timedelta(days=29)
        self._validate_range(start, end)

        code = self._extract_short_code(value)
        if code is not None:
            row = self.urls.get_by_short_code(code)
            rows = [row] if row is not None else []
        else:
            long_url = self._normalize_destination(value)
            rows = self.urls.get_by_destination(long_url) if long_url else []

        active_rows = [row for row in rows if self._is_active(row)]
        if not active_rows:
            raise PublicAnalyticsNotFoundError("no active link found")

        totals = {
            start + timedelta(days=offset): 0
            for offset in range((end - start).days + 1)
        }
        for row in active_rows:
            for item in self.analytics.daily_counts(row.short_code, start, end):
                totals[item["date"]] += item["clicks"]
        daily = [{"date": day, "clicks": clicks} for day, clicks in totals.items()]
        return {
            "matched_links": len(active_rows),
            "total_clicks": sum(totals.values()),
            "daily": daily,
        }

    @staticmethod
    def _validate_range(start: date, end: date) -> None:
        days = (end - start).days + 1
        if days < 1 or days > settings.analytics_max_range_days:
            raise AnalyticsRangeError(
                f"date range must be between 1 and {settings.analytics_max_range_days} days"
            )

    @staticmethod
    def _is_active(row) -> bool:
        if row is None or row.is_enabled is False:
            return False
        expiration = row.expiration_at
        if expiration is None:
            return True
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=UTC)
        return expiration > datetime.now(UTC)

    @staticmethod
    def _extract_short_code(value: str) -> str | None:
        if ALIAS_PATTERN.fullmatch(value):
            return value

        candidate = urlsplit(value)
        base = urlsplit(settings.public_base_url.rstrip("/"))
        if not candidate.scheme or not candidate.netloc:
            return None
        try:
            candidate_origin = (
                candidate.scheme.lower(),
                candidate.hostname,
                candidate.port,
            )
            base_origin = (base.scheme.lower(), base.hostname, base.port)
        except ValueError:
            return None
        if candidate_origin != base_origin:
            return None
        base_path = base.path.rstrip("/")
        path = candidate.path
        if base_path:
            if not path.startswith(f"{base_path}/"):
                return None
            path = path[len(base_path) :]
        parts = [unquote(part) for part in path.split("/") if part]
        if candidate.query or candidate.fragment or len(parts) != 1:
            return None
        return parts[0] if ALIAS_PATTERN.fullmatch(parts[0]) else None

    @staticmethod
    def _normalize_destination(value: str) -> str | None:
        try:
            return str(TypeAdapter(HttpUrl).validate_python(value))
        except ValidationError:
            return None
