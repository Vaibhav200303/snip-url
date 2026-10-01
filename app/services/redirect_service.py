import logging
from datetime import UTC, datetime

from app.repositories.url_cache import UrlCache
from app.repositories.url_repository import UrlRepository

logger = logging.getLogger(__name__)

class UrlNotFoundError(Exception):
    pass


class UrlExpiredError(Exception):
    pass


class UrlDisabledError(Exception):
    pass


class RedirectService:
    def __init__(
        self,
        repository: UrlRepository,
        cache: UrlCache,
    ):
        self.repository = repository
        self.cache = cache

    def get_long_url(self, short_code: str) -> str:
        # 1. Check Redis
        cached_url = self.cache.get(short_code)

        if cached_url is not None:
            logger.info("Cache hit", extra={"short_code": short_code})
            return cached_url
        
        logger.info("Cache miss", extra={"short_code": short_code})
        # 2. Cache miss → Cassandra
        row = self.repository.get_by_short_code(short_code)

        if row is None:
            raise UrlNotFoundError("Short URL not found")

        if row.is_enabled is False:
            raise UrlDisabledError("Short URL is disabled")

        # 3. Check expiration

        expiration_at = row.expiration_at

        if expiration_at is not None:
            if expiration_at.tzinfo is None:
                expiration_at = expiration_at.replace(tzinfo=UTC)

            if expiration_at <= datetime.now(UTC):
                raise UrlExpiredError("Short URL has expired")
        # 4. Populate Redis
        ttl = self._calculate_ttl(row.expiration_at)

        if ttl > 0:
            self.cache.set(
                short_code,
                row.long_url,
                ttl,
            )

        return row.long_url

    def _calculate_ttl(
        self,
        expiration_at: datetime | None,
    ) -> int:
        if expiration_at is None:
            from app.config.settings import settings

            return settings.cache_ttl_seconds

        if expiration_at.tzinfo is None:
            expiration_at = expiration_at.replace(
                tzinfo=UTC
            )

        remaining = (
            expiration_at - datetime.now(UTC)
        ).total_seconds()

        from app.config.settings import settings

        return max(0, min(int(remaining), settings.cache_ttl_seconds))
