FROM python:3.12-slim

ARG SERVICE_NAME

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./

# System dependencies for building some Python packages and TLS/FFI
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    git \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# If SERVICE_NAME is provided, run that MCP server; otherwise run the obs-app
CMD sh -lc 'if [ -n "${SERVICE_NAME}" ]; then python -m mcp_servers.${SERVICE_NAME}.server; else uvicorn obs_app.app:app --host 0.0.0.0 --port 8000; fi'
