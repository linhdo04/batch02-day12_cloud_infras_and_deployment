import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("AGENT_API_KEY", "unit-test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app import main
from app.auth import verify_api_key
from app.cost_guard import estimate_cost
from utils.mock_llm import ask as mock_ask


def test_health_endpoint_returns_ok():
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ask_requires_api_key(monkeypatch):
    main._is_ready = True
    monkeypatch.setattr(main, "check_rate_limit", lambda user_id: {"remaining": 9})
    monkeypatch.setattr(main, "get_history", lambda user_id: [])
    monkeypatch.setattr(
        main,
        "reserve_cost",
        lambda user_id, estimated_cost: {"remaining_usd": 9.99},
    )
    monkeypatch.setattr(main, "append_message", lambda user_id, role, content: None)
    client = TestClient(main.app)

    response = client.post(
        "/ask",
        json={"user_id": "student", "question": "Hello"},
    )

    assert response.status_code == 401


def test_ask_uses_redis_backed_history(monkeypatch):
    main._is_ready = True
    saved_messages = []
    monkeypatch.setattr(main, "check_rate_limit", lambda user_id: {"remaining": 8})
    monkeypatch.setattr(
        main,
        "get_history",
        lambda user_id: [{"role": "user", "content": "Hello from test"}],
    )
    monkeypatch.setattr(
        main,
        "reserve_cost",
        lambda user_id, estimated_cost: {"remaining_usd": 9.99},
    )
    monkeypatch.setattr(
        main,
        "append_message",
        lambda user_id, role, content: saved_messages.append((user_id, role, content)),
    )
    client = TestClient(main.app)

    response = client.post(
        "/ask",
        headers={"X-API-Key": "unit-test-key"},
        json={"user_id": "student", "question": "What did I just say?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == 'Your previous message was: "Hello from test"'
    assert body["history_messages"] == 3
    assert saved_messages[0] == ("student", "user", "What did I just say?")
    assert saved_messages[1][1] == "assistant"


def test_invalid_payload_returns_422():
    client = TestClient(main.app)

    response = client.post(
        "/ask",
        headers={"X-API-Key": "unit-test-key"},
        json={"user_id": "bad user id", "question": ""},
    )

    assert response.status_code == 422


def test_verify_api_key_rejects_invalid_key():
    try:
        verify_api_key("wrong-key")
    except Exception as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("invalid API key should be rejected")


def test_estimate_cost_uses_input_and_output_token_prices():
    cost = estimate_cost(input_tokens=1000, output_tokens=1000)

    assert cost == pytest.approx(0.00075)


def test_mock_llm_has_deterministic_keyword_responses():
    assert "portable container" in mock_ask("What is Docker?", delay=0)
    assert "public endpoint" in mock_ask("How to deploy?", delay=0)
