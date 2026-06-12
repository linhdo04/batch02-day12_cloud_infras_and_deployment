"""Validate the Day 12 final project.

Run static and Docker checks:
    python check_production_ready.py

Also test a running stack at http://localhost:8000:
    python check_production_ready.py --runtime
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path


BASE = Path(__file__).resolve().parent
MAX_IMAGE_BYTES = 500 * 1024 * 1024


class Report:
    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def check(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append((name, passed, detail))
        icon = "PASS" if passed else "FAIL"
        suffix = f" - {detail}" if detail else ""
        print(f"  [{icon}] {name}{suffix}")

    def finish(self) -> bool:
        passed = sum(result[1] for result in self.results)
        total = len(self.results)
        print(f"\nResult: {passed}/{total} checks passed")
        return passed == total


def read(relative_path: str) -> str:
    return (BASE / relative_path).read_text(encoding="utf-8")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=BASE,
        capture_output=True,
        text=True,
        check=False,
    )


def static_checks(report: Report) -> None:
    print("\nRequired files")
    required = [
        "app/main.py",
        "app/config.py",
        "app/auth.py",
        "app/rate_limiter.py",
        "app/cost_guard.py",
        "app/storage.py",
        "utils/mock_llm.py",
        "Dockerfile",
        "docker-compose.yml",
        "nginx/nginx.conf",
        "requirements.txt",
        ".env.example",
        ".dockerignore",
        "railway.toml",
        "render.yaml",
        "README.md",
    ]
    for path in required:
        report.check(path, (BASE / path).is_file())

    print("\nApplication")
    main = read("app/main.py")
    config = read("app/config.py")
    storage = read("app/storage.py")
    limiter = read("app/rate_limiter.py")
    guard = read("app/cost_guard.py")
    auth = read("app/auth.py")
    report.check("GET /health", '@app.get("/health")' in main)
    report.check("GET /ready", '@app.get("/ready")' in main)
    report.check("POST /ask", '@app.post("/ask"' in main)
    report.check("API-key authentication", "compare_digest" in auth and "401" in auth)
    report.check(
        "Redis sliding-window rate limit",
        "ZREMRANGEBYSCORE" in limiter and "ZCARD" in limiter and "429" in limiter,
    )
    report.check(
        "Monthly Redis cost guard",
        "INCRBYFLOAT" in guard and "Monthly budget exceeded" in guard and "402" in guard,
    )
    report.check(
        "Conversation history in Redis",
        "lrange" in storage and "rpush" in storage and "conversation:" in storage,
    )
    report.check("Structured JSON events", "json.dumps" in main and "log_event" in main)
    report.check(
        "Graceful SIGTERM lifecycle",
        "SIGTERM" in main and "graceful_shutdown_complete" in main,
    )
    report.check(
        "Environment configuration",
        'os.getenv("AGENT_API_KEY", "")' in config
        and 'os.getenv("REDIS_URL"' in config,
    )

    secret_pattern = re.compile(r"(sk-[A-Za-z0-9_-]{8,}|password\\s*=\\s*['\"][^'\"]+)")
    source = "\n".join(path.read_text(encoding="utf-8") for path in (BASE / "app").glob("*.py"))
    report.check("No hardcoded production secrets", secret_pattern.search(source) is None)

    root_gitignore = BASE.parent / ".gitignore"
    ignored = root_gitignore.is_file() and ".env" in root_gitignore.read_text(encoding="utf-8")
    report.check(".env ignored by Git", ignored)

    print("\nContainers")
    dockerfile = read("Dockerfile")
    compose = read("docker-compose.yml")
    report.check(
        "Multi-stage Dockerfile",
        len(re.findall(r"^FROM ", dockerfile, flags=re.MULTILINE | re.IGNORECASE)) >= 2,
    )
    report.check("Slim runtime image", "python:3.11-slim" in dockerfile)
    report.check("Non-root runtime user", "USER agent" in dockerfile)
    report.check("Docker HEALTHCHECK", "HEALTHCHECK" in dockerfile)
    report.check("Compose includes agent", re.search(r"^  agent:", compose, re.MULTILINE) is not None)
    report.check("Compose includes Redis", re.search(r"^  redis:", compose, re.MULTILINE) is not None)
    report.check("Compose includes Nginx", re.search(r"^  nginx:", compose, re.MULTILINE) is not None)

    compose_result = run(["docker", "compose", "config"])
    report.check(
        "docker compose config",
        compose_result.returncode == 0,
        compose_result.stderr.strip() if compose_result.returncode else "",
    )

    image_result = run(
        ["docker", "image", "inspect", "06-lab-complete-agent", "--format={{.Size}}"]
    )
    if image_result.returncode == 0:
        size = int(image_result.stdout.strip())
        report.check("Docker image under 500 MB", size < MAX_IMAGE_BYTES, f"{size / 1024 / 1024:.1f} MB")
    else:
        report.check("Docker image under 500 MB", False, "build image first")


def http_request(
    path: str,
    method: str = "GET",
    payload: dict[str, str] | None = None,
    authenticated: bool = False,
) -> tuple[int, dict]:
    headers: dict[str, str] = {}
    if authenticated:
        headers["X-API-Key"] = os.getenv("AGENT_API_KEY", "local-development-key")
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    request = urllib.request.Request(
        os.getenv("BASE_URL", "http://localhost:8000") + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def runtime_checks(report: Report) -> None:
    print("\nRuntime")
    health_status, _ = http_request("/health")
    ready_status, ready = http_request("/ready")
    report.check("Health returns 200", health_status == 200)
    report.check("Readiness returns 200 with Redis", ready_status == 200 and ready.get("storage") == "redis")

    user = f"verify-{uuid.uuid4().hex[:8]}"
    no_auth, _ = http_request(
        "/ask", "POST", {"user_id": user, "question": "hello"}, authenticated=False
    )
    invalid, _ = http_request("/ask", "POST", {"invalid": "data"}, authenticated=True)
    report.check("Missing API key returns 401", no_auth == 401)
    report.check("Invalid payload returns 422", invalid == 422)

    first_status, _ = http_request(
        "/ask",
        "POST",
        {"user_id": user, "question": "My first message"},
        authenticated=True,
    )
    second_status, second = http_request(
        "/ask",
        "POST",
        {"user_id": user, "question": "What did I just say?"},
        authenticated=True,
    )
    report.check(
        "Conversation context survives requests",
        first_status == 200
        and second_status == 200
        and "My first message" in second.get("answer", ""),
    )

    rate_user = f"rate-{uuid.uuid4().hex[:8]}"
    statuses = [
        http_request(
            "/ask",
            "POST",
            {"user_id": rate_user, "question": f"request {index}"},
            authenticated=True,
        )[0]
        for index in range(1, 12)
    ]
    report.check("Rate limit returns 429", statuses[:10] == [200] * 10 and statuses[10] == 429)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", action="store_true", help="also test a running local stack")
    args = parser.parse_args()

    print("Day 12 Production Readiness Check")
    report = Report()
    static_checks(report)
    if args.runtime:
        runtime_checks(report)
    return 0 if report.finish() else 1


if __name__ == "__main__":
    sys.exit(main())
