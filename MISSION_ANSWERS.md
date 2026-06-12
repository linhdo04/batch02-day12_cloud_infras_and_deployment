# Day 12 Lab - Mission Answers

**Student name:** Đỗ Thiện Lĩnh
**Student ID:** 2A202600775
**Completion date:** 12/06/2026

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

File `01-localhost-vs-production/develop/app.py` có các vấn đề:

1. Hardcode `OPENAI_API_KEY` trong source.
2. Hardcode database URL gồm username và password.
3. In API key ra log, làm lộ secret.
4. Config như `DEBUG` và `MAX_TOKENS` không đọc từ environment.
5. Dùng `print()` thay cho structured logging.
6. Không có `/health` và `/ready`.
7. Bind vào `localhost`, container bên ngoài không truy cập được.
8. Hardcode port `8000`, không dùng biến `PORT` do cloud inject.
9. Luôn bật reload/debug.
10. Không có input validation và error response rõ ràng.
11. Không có graceful shutdown/cleanup.
12. Không có authentication, rate limiting hoặc cost guard.

### Exercise 1.2: Basic version

Basic version chạy được trên local và trả response từ mock LLM. Tuy nhiên,
việc một process trả response trên laptop chưa chứng minh nó production-ready,
vì app chưa có health probe, external config, secret management và lifecycle.

### Exercise 1.3: Develop/production comparison

| Feature    | Develop                           | Production                         | Tại sao quan trọng?                      |
| ---------- | --------------------------------- | ---------------------------------- | ---------------------------------------- |
| Config     | Hardcode trong source             | Đọc environment variables          | Cùng image chạy được ở dev/staging/prod  |
| Secrets    | Có key và password trong code/log | Secret được inject qua environment | Tránh lộ credential trong Git và log     |
| Network    | `localhost:8000`                  | `0.0.0.0:$PORT`                    | Container/cloud có thể route traffic     |
| Health     | Không có                          | `/health` và `/ready`              | Platform biết khi nào restart hoặc route |
| Logging    | `print()`                         | Structured JSON events             | Log aggregator có thể search và parse    |
| Shutdown   | Dừng đột ngột                     | Uvicorn SIGTERM + lifespan cleanup | Hoàn thành request và đóng connection    |
| Validation | Query string không kiểm tra       | Pydantic model                     | Trả lỗi 422 rõ ràng, giảm input xấu      |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image của basic Dockerfile là `python:3.11`.
2. Working directory là `/app`.
3. Copy `requirements.txt` trước source để Docker cache layer cài dependency.
   Khi chỉ sửa code, layer `pip install` không phải chạy lại.
4. `CMD` cung cấp command mặc định và dễ bị override khi `docker run`.
   `ENTRYPOINT` xác định executable chính; argument của `docker run` thường
   được nối vào entrypoint.

### Exercise 2.2-2.3: Build and image size

Đo bằng `docker image inspect` trên máy ARM64 ngày 12/06/2026:

| Image                    | Base/build                     |       Size |
| ------------------------ | ------------------------------ | ---------: |
| `day12-agent:develop`    | Single-stage `python:3.11`     | 1090.2 MiB |
| `day12-agent:production` | Multi-stage `python:3.11-slim` |  179.3 MiB |

Production image nhỏ hơn **83.6%** và đạt yêu cầu dưới 500 MB.

Stage builder tạo virtualenv và cài dependencies. Stage runtime bắt đầu từ
slim image sạch, chỉ copy virtualenv và application source, rồi chạy bằng
non-root user. Build tools và cache không đi vào final image.

### Exercise 2.4: Docker Compose architecture

```text
Client :80
    |
    v
 Nginx
    |
    v
 FastAPI agent
    |
    v
  Redis
```

Nginx reverse proxy request tới agent qua Docker network. Agent dùng Redis
cho shared state/cache. Redis không publish port ra host. Healthcheck và
`depends_on` ngăn Nginx/agent nhận traffic trước khi dependency sẵn sàng.

Kết quả chạy stack thực tế:

```text
GET  /health -> 200
POST /ask    -> 200 {"answer":"Mock agent received: What is Docker?"}
```

## Part 3: Cloud Deployment

### Exercise 3.1: Railway

Application đã có:

- `railway.toml`
- Dockerfile production
- `/health` endpoint
- `PORT` đọc từ environment
- `REDIS_URL` và `AGENT_API_KEY` đọc từ environment

Public deployment:

- URL: https://agent-api-production-065b.up.railway.app
- Platform: Railway
- Redis: Railway Redis service qua `${{Redis.REDIS_URL}}`
- Screenshot: [screenshots/public-health.png](screenshots/public-health.png)

Kết quả checker chạy trực tiếp trên URL public:

```text
Health 200, readiness 200, auth 401/200, validation 422
Conversation context passed, request 11 returned 429
Result: 43/43 checks passed
```

### Exercise 3.2: Railway and Render comparison

| Aspect  | `railway.toml`                   | `render.yaml`                      |
| ------- | -------------------------------- | ---------------------------------- |
| Format  | TOML                             | YAML Blueprint                     |
| Build   | Dockerfile builder               | Docker runtime, có `rootDir`       |
| Start   | Có thể override `startCommand`   | Dùng Dockerfile command            |
| Health  | `healthcheckPath`                | `healthCheckPath`                  |
| Secrets | Set bằng CLI/dashboard           | `sync: false` hoặc generated value |
| Redis   | Add database service, inject URL | Tạo Key Value service, set URL     |

### Exercise 3.3: Cloud Run CI/CD

`cloudbuild.yaml` mô tả pipeline build image, push vào registry và deploy.
`service.yaml` mô tả Cloud Run service, container port, resource và scaling.
So với Railway/Render, Cloud Run cần cấu hình IAM/project/registry nhiều hơn
nhưng phù hợp production và CI/CD có kiểm soát.

## Part 4: API Security

### Exercise 4.1: API key

API key được đọc từ header `X-API-Key` bằng `APIKeyHeader`. Hàm dependency
so sánh constant-time với secret từ environment. Thiếu hoặc sai key trả 401.
Rotate key bằng cách đổi `AGENT_API_KEY` trên platform và restart/rolling
deploy, không sửa source.

Kết quả runtime Final Project:

```text
POST /ask without X-API-Key -> 401
POST /ask with valid key    -> 200
```

### Exercise 4.2: JWT flow

1. Client gửi username/password tới token endpoint.
2. Server xác thực user và ký JWT chứa `sub`, `role`, `iat`, `exp`.
3. Client gửi `Authorization: Bearer <token>`.
4. Server verify signature/expiry và lấy username/role.
5. Token hết hạn trả 401; token sai signature trả 403.

### Exercise 4.3: Rate limiting

Ví dụ Part 4 dùng sliding window trong memory: user 10 request/phút, admin
100 request/phút. Final Project nâng cấp thành Redis sorted set với Lua
atomic transaction để nhiều instance dùng chung một quota.

Kết quả 11 request liên tiếp cho cùng user:

```text
200 200 200 200 200 200 200 200 200 200 429
```

Admin bypass không nên là bỏ hoàn toàn protection. Cách phù hợp là gán tier
riêng với limit cao hơn dựa trên role/credential đã xác thực.

### Exercise 4.4: Cost guard

Implementation cuối dùng key `budget:<user_id>:<YYYY-MM>` trong Redis.
Lua script đọc spending hiện tại, so sánh `current + estimated_cost` với
10 USD, sau đó `INCRBYFLOAT` atomically. Key hết hạn sau khi tháng kết thúc.

Kết quả khi spending tháng được đặt bằng 10 USD:

```text
POST /ask -> 402
{"error":"Monthly budget exceeded","spent_usd":10.0,"budget_usd":10.0}
```

## Part 5: Scaling and Reliability

### Exercise 5.1: Health checks

- `/health`: liveness, chỉ xác nhận process đang sống và trả metadata.
- `/ready`: ping Redis; trả 200 khi có thể nhận traffic, 503 nếu dependency
  chưa sẵn sàng.

Runtime result:

```text
GET /health -> 200 {"status":"ok", ...}
GET /ready  -> 200 {"status":"ready","storage":"redis", ...}
```

### Exercise 5.2: Graceful shutdown

Uvicorn nhận SIGTERM, ngừng nhận request mới, chờ in-flight request theo
`--timeout-graceful-shutdown 30`, rồi chạy lifespan cleanup và đóng Redis.

Log đã quan sát:

```text
Shutting down
{"event":"graceful_shutdown_started","in_flight":0}
{"event":"graceful_shutdown_complete"}
Finished server process
```

### Exercise 5.3: Stateless design

Conversation history không nằm trong dictionary của process. Mỗi message
được serialize JSON và lưu trong Redis list `conversation:<user_id>`.
Rate limit và cost usage cũng ở Redis, nên mọi instance nhìn thấy cùng state.

### Exercise 5.4: Load balancing

Stack được chạy bằng:

```bash
docker compose up --build --scale agent=3 -d
```

Ba instance đã phục vụ cùng một test:

```text
5a574cf0b1d4
76d7aa6d7f39
a28c42fe25b1
```

Nginx phân phối request tới cả ba instance.

### Exercise 5.5: Stateless failure test

1. Tạo conversation trên instance thứ nhất.
2. Follow-up được phục vụ bởi instance thứ hai và vẫn đọc đúng message trước.
3. Dừng một agent bằng SIGTERM.
4. Gửi tiếp request qua Nginx.
5. Request vẫn trả 200 và history vẫn còn trong Redis.

Ví dụ context response:

```text
Your previous message was: "Hello from turn one"
```

Ngoài Final Project, stack riêng của Part 5 cũng được build với ba replica.
Năm request liên tiếp đi qua ba instance khác nhau và endpoint history trả
đủ 10 message:

```text
Instances used: instance-3f4ac7, instance-80fe53, instance-f052cc
Total messages: 10
```

## Final Project Validation

```text
python check_production_ready.py           -> 37/37 passed
python check_production_ready.py --runtime -> 43/43 passed
Public Railway runtime                     -> 43/43 passed
Docker image                               -> 181.8 MiB
Runtime user                               -> agent (non-root)
```
