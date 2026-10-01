import logging

from redis import RedisError

from app.database.redis.connection import redis_client

logger = logging.getLogger(__name__)


class RateLimitExceededError(Exception):
    pass


class RateLimiter:
    SCRIPT = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return count
    """

    def check(self, scope: str, identity: str, limit: int, window: int) -> None:
        key = f"rate:{scope}:{identity}"
        try:
            count = redis_client.eval(self.SCRIPT, 1, key, window)
            if count > limit:
                raise RateLimitExceededError("rate limit exceeded")
        except RateLimitExceededError:
            raise
        except RedisError:
            logger.warning("Redis rate limiter failed open", exc_info=True)
