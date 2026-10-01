import logging

from redis import RedisError

from app.database.redis.connection import redis_client

logger = logging.getLogger(__name__)


class UrlCache:
    PREFIX = "url:"
    DEFAULT_TTL = 3600

    def get(self, short_code: str) -> str | None:
        try:
            return redis_client.get(f"{self.PREFIX}{short_code}")
        except RedisError:
            logger.warning("Redis cache read failed", exc_info=True)
            return None

    def set(
        self,
        short_code: str,
        long_url: str,
        ttl: int = DEFAULT_TTL,
    ) -> None:
        try:
            redis_client.set(f"{self.PREFIX}{short_code}", long_url, ex=ttl)
        except RedisError:
            logger.warning("Redis cache write failed", exc_info=True)

    def delete(self, short_code: str) -> None:
        try:
            redis_client.delete(f"{self.PREFIX}{short_code}")
        except RedisError:
            logger.warning("Redis cache delete failed", exc_info=True)
