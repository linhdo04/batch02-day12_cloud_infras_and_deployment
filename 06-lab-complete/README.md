# Lab 12 - Production-Ready AI Agent

Final project kết hợp Docker, Redis, API security, cost protection, health
checks, graceful shutdown và horizontal scaling.

## Architecture

```text
Client -> Nginx -> Agent 1 --+
                -> Agent 2 --+-> Redis
                -> Agent 3 --+
```

Redis lưu conversation history, sliding-window rate limit và monthly budget.
Vì agent không giữ state nghiệp vụ trong memory, request tiếp theo có thể được
xử lý bởi bất kỳ instance nào.

## Features

- `POST /ask` với API key và Pydantic validation
- Conversation history theo `user_id`
- Redis sliding-window rate limit: 10 requests/phút/user
- Redis cost guard: 10 USD/tháng/user
- `GET /health` và `GET /ready`
- Structured JSON application logs
- Graceful SIGTERM shutdown
- Multi-stage Dockerfile, non-root runtime
- Docker Compose gồm Nginx, nhiều agent và Redis
- Cấu hình Railway và Render

## Run Locally

```bash
cd 06-lab-complete
cp .env.example .env

# Đổi AGENT_API_KEY trong .env, sau đó:
docker compose up --build --scale agent=3 -d
docker compose ps
```

Compose đọc `.env` tự động. Nếu chưa tạo file này, local key mặc định của
Compose là `local-development-key`.

```bash
export AGENT_API_KEY=local-development-key

curl http://localhost:8000/health
curl http://localhost:8000/ready

curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"student","question":"What is deployment?"}'
```

Kiểm tra context:

```bash
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"student","question":"What did I just say?"}'
```

## Verification

```bash
python check_production_ready.py
AGENT_API_KEY=local-development-key python check_production_ready.py --runtime
```

Test graceful shutdown và stateless behavior:

```bash
docker stop --time 10 06-lab-complete-agent-1
docker logs 06-lab-complete-agent-1

# Các instance còn lại vẫn đọc được conversation từ Redis.
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"student","question":"What was my previous message?"}'
```

## Deploy

### Railway

Chạy từ thư mục `06-lab-complete`:

```bash
railway login
railway init
railway add --database redis
railway variables set ENVIRONMENT=production
railway variables set AGENT_API_KEY=<strong-random-secret>
railway variables set RATE_LIMIT_PER_MINUTE=10
railway variables set MONTHLY_BUDGET_USD=10
railway up
railway domain
```

Đặt `REDIS_URL` bằng connection URL của Redis service nếu Railway không tự
inject biến này.

Deployment của bài nộp:

```text
https://agent-api-production-065b.up.railway.app
```

Public deployment đã qua toàn bộ `43/43` static và runtime checks.

### Render

1. Push repository lên GitHub.
2. Render Dashboard -> New -> Blueprint.
3. Chọn repository và Blueprint path `06-lab-complete/render.yaml`.
4. Blueprint tạo web service cùng Key Value miễn phí và nối `REDIS_URL`
   bằng private connection string.
5. Sau khi deploy, lấy `AGENT_API_KEY` trong Environment và test `/health`.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | HTTP port |
| `ENVIRONMENT` | `development` | Runtime environment |
| `ENABLE_DOCS` | `true` | Enable Swagger UI at `/docs` |
| `AGENT_API_KEY` | empty | Required secret in production |
| `REDIS_URL` | `redis://localhost:6379/0` | Shared state |
| `RATE_LIMIT_PER_MINUTE` | `10` | Per-user request limit |
| `MONTHLY_BUDGET_USD` | `10.0` | Per-user monthly budget |
| `CONVERSATION_TTL_SECONDS` | `2592000` | History retention |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowlist |

The included mock LLM works without an external API key.
