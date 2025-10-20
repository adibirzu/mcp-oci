FROM python:3.11-slim

# Environment and non-interactive apt
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# System deps needed for building wheels and common libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential curl git libssl-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies via pip (avoid Poetry inside container to prevent build failures)
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose WebSocket ports for MCP servers (multi-user) and Prometheus metrics ports
EXPOSE 7001 7002 7003 7004 7005 7006 7007 7008 7009 7011
EXPOSE 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011

# Default command: start all MCP servers in daemon mode; can be overridden by k8s/CI
CMD ["bash", "-lc", "scripts/mcp-launchers/start-mcp-server.sh all --daemon && sleep infinity"]
