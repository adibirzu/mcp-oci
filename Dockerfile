FROM python:3.12-slim

ARG SERVICE_NAME

# Environment and non-interactive apt
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# System deps needed for building wheels and common libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential curl git libssl-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies via pip (avoid Poetry inside container to prevent build failures)
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose WebSocket ports for MCP servers (multi-user) and Prometheus metrics ports
EXPOSE 7001 7002 7003 7004 7005 7006 7007 7008 7009 7011
EXPOSE 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011

# If SERVICE_NAME is provided, run that MCP server; otherwise start all servers in daemon mode
CMD sh -lc 'if [ -n "${SERVICE_NAME}" ]; then python -m mcp_servers.${SERVICE_NAME}.server; else scripts/mcp-launchers/start-mcp-server.sh all --daemon && sleep infinity; fi'
