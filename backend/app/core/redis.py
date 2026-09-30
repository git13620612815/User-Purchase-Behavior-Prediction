import redis

from app.core.config import settings

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def redis_ok() -> bool:
    try:
        return bool(redis_client.ping())
    except redis.RedisError:
        return False
