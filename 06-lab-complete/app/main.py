"""Production-ready, stateless AI agent for the Day 12 final project.

Uvicorn owns SIGTERM handling and invokes the lifespan shutdown hook after
it finishes in-flight requests.
"""
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import estimate_cost, get_usage, reserve_cost
from app.rate_limiter import check_rate_limit
from app.storage import append_message, clear_history, get_history, ping_redis, redis_client
from utils.mock_llm import ask as llm_ask


logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0
_in_flight_requests = 0


def log_event(event: str, **fields: object) -> None:
    logger.info(json.dumps({"event": event, **fields}, ensure_ascii=False))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _is_ready
    log_event(
        "startup",
        app=settings.app_name,
        version=settings.app_version,
        instance=settings.instance_id,
    )
    try:
        ping_redis()
    except redis.RedisError as exc:
        log_event("redis_unavailable", error=str(exc))
    else:
        _is_ready = True
        log_event("ready", storage="redis")

    yield

    _is_ready = False
    log_event("graceful_shutdown_started", in_flight=_in_flight_requests)
    redis_client.close()
    log_event("graceful_shutdown_complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count, _in_flight_requests
    started = time.time()
    _request_count += 1
    _in_flight_requests += 1
    try:
        response: Response = await call_next(request)
    except Exception:
        _error_count += 1
        log_event("request_failed", method=request.method, path=request.url.path)
        raise
    finally:
        _in_flight_requests -= 1

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    log_event(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.time() - started) * 1000, 1),
        instance=settings.instance_id,
    )
    return response


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    history_messages: int
    served_by: str
    model: str
    rate_limit_remaining: int
    budget_remaining_usd: float
    timestamp: str


def answer_with_context(question: str, history: list[dict[str, object]]) -> str:
    normalized = question.strip().lower()
    recall_prompts = (
        "what did i just say",
        "what was my previous message",
        "tôi vừa nói gì",
        "tin nhắn trước của tôi",
    )
    previous_user_messages = [
        str(message["content"]) for message in history if message.get("role") == "user"
    ]
    if any(prompt in normalized for prompt in recall_prompts) and previous_user_messages:
        return f'Your previous message was: "{previous_user_messages[-1]}"'
    return llm_ask(question)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance": settings.instance_id,
        "endpoints": {"ask": "POST /ask", "health": "GET /health", "ready": "GET /ready"},
    }


@app.post("/ask", response_model=AskResponse)
def ask_agent(body: AskRequest, _auth: str = Depends(verify_api_key)):
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Service is not ready")

    try:
        rate_info = check_rate_limit(body.user_id)
        history = get_history(body.user_id)
        answer = answer_with_context(body.question, history)
        input_tokens = max(1, len(body.question.split()) * 2)
        output_tokens = max(1, len(answer.split()) * 2)
        budget_info = reserve_cost(
            body.user_id,
            estimate_cost(input_tokens=input_tokens, output_tokens=output_tokens),
        )
        append_message(body.user_id, "user", body.question)
        append_message(body.user_id, "assistant", answer)
        history_count = len(history) + 2
    except redis.RedisError as exc:
        log_event("redis_operation_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Storage dependency unavailable") from exc

    log_event(
        "agent_call",
        user_id=body.user_id,
        question_length=len(body.question),
        history_messages=history_count,
    )
    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        history_messages=history_count,
        served_by=settings.instance_id,
        model=settings.llm_model,
        rate_limit_remaining=rate_info["remaining"],
        budget_remaining_usd=budget_info["remaining_usd"],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/conversations/{user_id}")
def conversation(user_id: str, _auth: str = Depends(verify_api_key)):
    try:
        messages = get_history(user_id)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Storage dependency unavailable") from exc
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"user_id": user_id, "messages": messages, "count": len(messages)}


@app.delete("/conversations/{user_id}")
def delete_conversation(user_id: str, _auth: str = Depends(verify_api_key)):
    try:
        deleted = clear_history(user_id)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Storage dependency unavailable") from exc
    return {"user_id": user_id, "deleted": deleted}


@app.get("/usage/{user_id}")
def usage(user_id: str, _auth: str = Depends(verify_api_key)):
    try:
        return {"user_id": user_id, **get_usage(user_id)}
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Storage dependency unavailable") from exc


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "instance": settings.instance_id,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Application startup is incomplete")
    try:
        ping_redis()
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc
    return {"status": "ready", "storage": "redis", "instance": settings.instance_id}


@app.get("/metrics")
def metrics(_auth: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "in_flight_requests": _in_flight_requests,
        "instance": settings.instance_id,
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
