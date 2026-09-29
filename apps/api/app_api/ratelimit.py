"""Fixed-window rate limiting on Redis (auth + public endpoints)."""

from functools import lru_cache

from fastapi import Request
from redis import Redis

from app_api.errors import ApiError
from app_core.settings import get_settings


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce(redis: Redis, key: str, limit: int, window_seconds: int = 60) -> None:
    bucket = f"rl:{key}"
    count = redis.incr(bucket)
    if count == 1:
        redis.expire(bucket, window_seconds)
    if count > limit:
        raise ApiError(
            429, "rate_limited", "Too many requests. Please wait a minute and try again."
        )
