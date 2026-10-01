import logging

from redis import RedisError

from app.database.redis.connection import redis_client

logger = logging.getLogger(__name__)


class RateLimitExceededError(Exception):
    pass


class RateLimiter:
    def check(self, scope: str, identity: str, limit: int, window: int) -> None:
        key = f"rate:{scope}:{identity}"
        try:
            with redis_client.pipeline(transaction=True) as pipeline:
                pipeline.incr(key)
                pipeline.expire(key, window)
                count, _ = pipeline.execute()
            if count > limit:
                raise RateLimitExceededError("rate limit exceeded")
        except RateLimitExceededError:
            raise
        except RedisError:
            logger.warning("Redis rate limiter failed open", exc_info=True)
