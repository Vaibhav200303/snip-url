import redis

from app.config.settings import settings

redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    decode_responses=True,
    socket_connect_timeout=0.25,
    socket_timeout=0.25,
)


def redis_ready() -> bool:
    try:
        return bool(redis_client.ping())
    except redis.RedisError:
        return False


def close_redis() -> None:
    redis_client.close()
