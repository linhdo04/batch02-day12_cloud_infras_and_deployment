"""Atomic Redis sliding-window rate limiter."""
import time
import uuid

from fastapi import HTTPException

from app.config import settings
from app.storage import redis_client


_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local cutoff = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local member = ARGV[3]
local limit = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    return {0, count, oldest[2] or now}
end

redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, ttl)
return {1, count + 1, now}
"""


def check_rate_limit(user_id: str) -> dict[str, int]:
    now_ms = int(time.time() * 1000)
    window_ms = 60_000
    key = f"rate_limit:{user_id}"
    allowed, count, oldest_ms = redis_client.eval(
        _SLIDING_WINDOW_SCRIPT,
        1,
        key,
        now_ms - window_ms,
        now_ms,
        f"{now_ms}:{uuid.uuid4().hex}",
        settings.rate_limit_per_minute,
        61,
    )

    if not allowed:
        retry_after = max(1, int((int(oldest_ms) + window_ms - now_ms) / 1000) + 1)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
                "X-RateLimit-Remaining": "0",
            },
        )

    return {
        "limit": settings.rate_limit_per_minute,
        "remaining": max(0, settings.rate_limit_per_minute - int(count)),
    }
