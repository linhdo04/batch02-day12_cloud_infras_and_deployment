# Deployment Information

## Public URL

https://agent-api-production-065b.up.railway.app

## Platform

Railway

- Project: `day12-production-agent`
- Service: `agent-api`
- Redis service: `Redis`
- Latest successful deployment: `92fef080-7677-4b14-9473-97e7e738d76e`
- Deployment date: **12/06/2026**

Railway build Dockerfile production, chạy healthcheck `/health` và kết nối
agent với Redis bằng reference variable `${{Redis.REDIS_URL}}`.

## Source Repository

https://github.com/linhdo04/batch02-day12_cloud_infras_and_deployment

## Test Commands

```bash
export URL=https://agent-api-production-065b.up.railway.app
export AGENT_API_KEY='<value stored securely in Railway>'

curl "$URL/health"
curl "$URL/ready"

curl -X POST "$URL/ask" \
  -H "X-API-Key: $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"deployment-test","question":"Hello"}'
```

Không commit `AGENT_API_KEY` vào repository. Giá trị thật được tạo ngẫu nhiên
64 ký tự và chỉ lưu trong Railway Variables.

## Environment Variables

- `PORT`
- `ENVIRONMENT=production`
- `ENABLE_DOCS=true`
- `AGENT_API_KEY`
- `REDIS_URL`
- `RATE_LIMIT_PER_MINUTE=10`
- `MONTHLY_BUDGET_USD=10`
- `ALLOWED_ORIGINS`
- `OPENAI_API_KEY` (optional; mock LLM hoạt động khi để trống)

## Verified Public Results

| Check                           | Result |
| ------------------------------- | ------ |
| `GET /health`                   | 200    |
| `GET /ready` with Railway Redis | 200    |
| Missing API key                 | 401    |
| Valid API key                   | 200    |
| Invalid payload                 | 422    |
| Conversation context            | Passed |
| Rate limit request 11           | 429    |
| Public readiness checker        | 43/43  |

## Verified Local Results

| Check                         | Result                           |
| ----------------------------- | -------------------------------- |
| Monthly budget exhausted      | 402                              |
| Conversation across instances | Passed                           |
| Graceful SIGTERM              | Passed                           |
| Part 2 Docker stack           | `/health` 200, `/ask` 200        |
| Part 5 scaling stack          | 3 instances, 10 history messages |
| Docker image size             | 181.8 MiB                        |

## CI/CD Bonus

GitHub Actions workflow: [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml)

| Stage              | Evidence                                                 |
| ------------------ | -------------------------------------------------------- |
| Lint               | `ruff check --select E9,F app utils tests`               |
| Unit test coverage | `pytest tests --cov=app --cov=utils --cov-fail-under=60` |
| Production check   | `python check_production_ready.py`                       |
| Deploy             | Railway CLI job after CI passes on `main`                |

Demo instructions and required GitHub secrets are documented in
[BONUS_CICD.md](BONUS_CICD.md).

## Screenshots

- Railway dashboard: [screenshots/railway-dashboard.png](screenshots/railway-dashboard.png)
- Public Railway health: [screenshots/public-health.png](screenshots/public-health.png)
- Local service: [screenshots/local-service.png](screenshots/local-service.png)
- Runtime verification: [screenshots/runtime-verification.png](screenshots/runtime-verification.png)
