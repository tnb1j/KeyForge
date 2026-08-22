# Production Hardened Multi-Stage Dockerfile for KeyForge Server
FROM python:3.12-slim AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final Runtime Stage
FROM python:3.12-slim AS runner

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH" \
    KEYFORGE_DB_URL="sqlite:////data/keyforge.db"

COPY --from=builder /root/.local /root/.local
COPY . /app

RUN mkdir -p /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')" || exit 1

ENTRYPOINT ["python", "-m", "keyforge.cli", "serve", "--host", "0.0.0.0", "--port", "8000"]
