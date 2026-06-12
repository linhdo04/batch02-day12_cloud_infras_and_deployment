# ============================================================
# ADVANCED Dockerfile — Multi-stage build
#
# Mục tiêu: image < 500 MB, secure, production-ready
#
# Tại sao multi-stage?
#   Stage 1 (builder): cần pip, gcc, build tools để compile deps
#   Stage 2 (runtime): chỉ cần Python và site-packages → nhỏ và sạch
# ============================================================

# ──────────────────────────────────────────────────────────
# STAGE 1: Builder
# Cài đặt tất cả dependencies
# Image này KHÔNG được dùng để deploy
# ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Copy và cài requirements
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ──────────────────────────────────────────────────────────
# STAGE 2: Runtime
# Chỉ copy những gì cần để CHẠY, không cần để BUILD
# ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Tạo non-root user — security best practice
# Chạy với root trong container là bad practice
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy virtual environment từ builder
COPY --from=builder /opt/venv /opt/venv

# Copy source code
COPY main.py .

# Copy utils from project root
COPY utils/ /app/utils/

# Đặt ownership cho appuser
RUN chown -R appuser:appuser /app

# Chuyển sang non-root user
USER appuser

ENV PATH=/opt/venv/bin:$PATH
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check — Docker sẽ tự restart nếu fail
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

# ============================================================
# Build commands (from project root):
#   cd ../../  # Go to project root
#   docker build -f 02-docker/production/Dockerfile -t agent-production .
#   docker images agent-production  ← kiểm tra size
#   docker run -p 8000:8000 -e ENVIRONMENT=production agent-production
# ============================================================
