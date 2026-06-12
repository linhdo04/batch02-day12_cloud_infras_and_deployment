# Day 12 Solution

Student: Đỗ Thiện Lĩnh  
Student ID: 2A202600775  
Date: 12/06/2026

This file mirrors the required codelab answers for Parts 1-5. Full runtime
evidence is recorded in `MISSION_ANSWERS.md`, `DEPLOYMENT.md`, and
`SUBMISSION_CHECKLIST.md`.

## Part 1: Localhost vs Production

| Exercise          | Answer                                                                                                                                                                                                        |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1 Anti-patterns | Hardcoded API key/database URL, secret logging, hardcoded port, debug/reload mode, no health checks, no readiness checks, no structured logging, no graceful shutdown, no auth, no rate limit, no cost guard. |
| 1.2 Basic version | The local app runs, but running locally does not prove production readiness because config, secrets, lifecycle, health probes, and cloud networking are missing.                                              |
| 1.3 Comparison    | Production uses environment variables, secret injection, `0.0.0.0:$PORT`, health/readiness endpoints, structured JSON logs, Pydantic validation, and graceful shutdown.                                       |

## Part 2: Docker

| Exercise        | Answer                                                                                                                                                                     |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2.1 Dockerfile  | Base image: `python:3.11`; workdir: `/app`; copying `requirements.txt` first improves layer cache; `CMD` is the default command while `ENTRYPOINT` defines the executable. |
| 2.2 Build/run   | Basic image was built and tested through `/ask`.                                                                                                                           |
| 2.3 Multi-stage | Builder installs dependencies into a virtualenv; runtime starts from `python:3.11-slim`, copies only app and venv, and runs as non-root. Production image is under 500 MB. |
| 2.4 Compose     | Nginx routes traffic to the FastAPI agent; the agent uses Redis over the internal Docker network; Redis does not expose a public host port.                                |

## Part 3: Cloud Deployment

| Exercise              | Answer                                                                                                                                                        |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3.1 Railway           | Public URL: `https://agent-api-production-065b.up.railway.app`; service and Redis are online.                                                                 |
| 3.2 Railway vs Render | Railway uses `railway.toml`; Render uses `render.yaml` blueprint. Both support Docker deploys, health checks, env vars, and managed Redis/Key Value services. |
| 3.3 Cloud Run         | `cloudbuild.yaml` defines image build/push/deploy; `service.yaml` defines Cloud Run service settings, container port, resources, and scaling.                 |

## Part 4: API Security

| Exercise          | Answer                                                                                                                                     |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 4.1 API key       | `X-API-Key` is checked with constant-time comparison. Missing or wrong keys return 401. Rotation is done by changing the platform secret.  |
| 4.2 JWT           | Client obtains a signed token, sends `Authorization: Bearer <token>`, and server verifies signature/expiry before authorizing the request. |
| 4.3 Rate limiting | Final project uses Redis sorted-set sliding window, 10 requests/minute per user, returning 429 when exceeded.                              |
| 4.4 Cost guard    | Final project tracks monthly spending in Redis key `budget:<user_id>:<YYYY-MM>` and returns 402 when monthly budget is exceeded.           |

## Part 5: Scaling and Reliability

| Exercise              | Answer                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------ |
| 5.1 Health checks     | `/health` is liveness; `/ready` checks Redis readiness.                                    |
| 5.2 Graceful shutdown | Uvicorn handles SIGTERM, waits for in-flight requests, then lifespan cleanup closes Redis. |
| 5.3 Stateless design  | Conversation, rate limit, and budget data are stored in Redis, not process memory.         |
| 5.4 Load balancing    | Docker Compose can scale `agent=3`; Nginx distributes traffic across instances.            |
| 5.5 Stateless test    | Conversation survives instance changes because all instances share Redis state.            |

## Bonus: CI/CD

Implemented in `.github/workflows/ci-cd.yml`.

| Requirement             | Implementation                               |
| ----------------------- | -------------------------------------------- |
| GitHub Actions pipeline | `Day 12 CI/CD` workflow                      |
| Lint                    | Ruff stage                                   |
| Unit test coverage      | Pytest with coverage gate                    |
| CD                      | Railway deploy job after CI passes on `main` |
| Demo notes              | `BONUS_CICD.md`                              |
