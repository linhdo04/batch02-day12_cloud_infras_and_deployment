FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime

RUN groupadd -r agent && useradd -r -g agent agent
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app.py .
COPY utils/ ./utils/
RUN chown -R agent:agent /app

USER agent
ENV PATH=/opt/venv/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready')" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
