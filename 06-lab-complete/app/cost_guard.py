"""Monthly per-user LLM cost protection backed by Redis."""
import calendar
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings
from app.storage import redis_client


INPUT_USD_PER_1K_TOKENS = 0.00015
OUTPUT_USD_PER_1K_TOKENS = 0.00060

_RESERVE_COST_SCRIPT = """
local key = KEYS[1]
local amount = tonumber(ARGV[1])
local budget = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local current = tonumber(redis.call('GET', key) or '0')

if current + amount > budget then
    return {0, tostring(current)}
end

local updated = redis.call('INCRBYFLOAT', key, amount)
redis.call('EXPIRE', key, ttl)
return {1, tostring(updated)}
"""


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens / 1000 * INPUT_USD_PER_1K_TOKENS
        + output_tokens / 1000 * OUTPUT_USD_PER_1K_TOKENS
    )


def _month_details() -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    _, days_in_month = calendar.monthrange(now.year, now.month)
    remaining_seconds = (
        (days_in_month - now.day + 1) * 24 * 60 * 60
        - now.hour * 60 * 60
        - now.minute * 60
        - now.second
    )
    return now.strftime("%Y-%m"), max(remaining_seconds, 60)


def reserve_cost(user_id: str, estimated_cost: float) -> dict[str, float]:
    month, ttl = _month_details()
    key = f"budget:{user_id}:{month}"
    allowed, raw_spent = redis_client.eval(
        _RESERVE_COST_SCRIPT,
        1,
        key,
        f"{estimated_cost:.10f}",
        f"{settings.monthly_budget_usd:.10f}",
        ttl,
    )
    spent = float(raw_spent)
    if not allowed:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "spent_usd": round(spent, 6),
                "budget_usd": settings.monthly_budget_usd,
                "month": month,
            },
        )
    return {
        "spent_usd": round(spent, 6),
        "remaining_usd": round(max(0.0, settings.monthly_budget_usd - spent), 6),
    }


def get_usage(user_id: str) -> dict[str, float | str]:
    month, _ = _month_details()
    spent = float(redis_client.get(f"budget:{user_id}:{month}") or 0)
    return {
        "month": month,
        "spent_usd": round(spent, 6),
        "budget_usd": settings.monthly_budget_usd,
        "remaining_usd": round(max(0.0, settings.monthly_budget_usd - spent), 6),
    }
