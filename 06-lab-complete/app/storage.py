"""Shared Redis connection and conversation storage."""
import json
from datetime import datetime, timezone
from typing import Any

import redis

from app.config import settings


redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
    health_check_interval=30,
)


def conversation_key(user_id: str) -> str:
    return f"conversation:{user_id}"


def ping_redis() -> bool:
    return bool(redis_client.ping())


def get_history(user_id: str) -> list[dict[str, Any]]:
    messages = redis_client.lrange(conversation_key(user_id), 0, -1)
    return [json.loads(message) for message in messages]


def append_message(user_id: str, role: str, content: str) -> None:
    message = json.dumps(
        {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        ensure_ascii=False,
    )
    key = conversation_key(user_id)
    with redis_client.pipeline(transaction=True) as pipe:
        pipe.rpush(key, message)
        pipe.ltrim(key, -settings.conversation_max_messages, -1)
        pipe.expire(key, settings.conversation_ttl_seconds)
        pipe.execute()


def clear_history(user_id: str) -> bool:
    return bool(redis_client.delete(conversation_key(user_id)))
