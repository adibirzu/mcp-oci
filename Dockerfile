# ──────────────────────────────────────────────────────────────────
# Multi-stage build for OCI MCP Server and Gateway
# Targets: OKE, OCI Container Instances, OCI Data Science, local
# ──────────────────────────────────────────────────────────────────
# Build:
#   docker build -t oci-mcp-server .
#   docker build --target gateway -t oci-mcp-gateway .
#
# Run (server):
#   docker run -p 8000:8000 -e OCI_MCP_TRANSPORT=streamable_http oci-mcp-server
#
# Run (gateway):
#   docker run -p 9000:9000 -v ./gateway.json:/app/gateway.json \
#     -e MCP_GATEWAY_CONFIG=/app/gateway.json oci-mcp-gateway
# ──────────────────────────────────────────────────────────────────

# ── Base stage ───────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system deps (OCI SDK needs gcc for some extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install all dependencies (including gateway and otel extras)
RUN uv sync --all-extras --no-dev --frozen --no-install-project

# Copy source code
COPY src/ src/

# Install the project itself
RUN uv sync --all-extras --no-dev --frozen

# ── MCP Server target ───────────────────────────────────────────
FROM base AS server

LABEL org.opencontainers.image.title="OCI MCP Server" \
      org.opencontainers.image.description="Oracle Cloud Infrastructure MCP Server with FastMCP" \
      org.opencontainers.image.version="2.0.0" \
      org.opencontainers.image.source="https://github.com/adibirzu/mcp-oci"

# Default: Streamable HTTP transport for container deployments
ENV OCI_MCP_TRANSPORT=streamable_http \
    OCI_MCP_PORT=8000 \
    OCI_MCP_LOG_LEVEL=INFO

EXPOSE 8000

# Health check: the server responds on the MCP endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/mcp'); assert r.status_code in (200, 405, 406)" || exit 1

ENTRYPOINT ["uv", "run", "python", "-m", "mcp_server_oci.server"]

# ── MCP Gateway target ──────────────────────────────────────────
FROM base AS gateway

LABEL org.opencontainers.image.title="OCI MCP Gateway" \
      org.opencontainers.image.description="MCP Gateway - Aggregating proxy for multiple MCP servers" \
      org.opencontainers.image.version="2.0.0" \
      org.opencontainers.image.source="https://github.com/adibirzu/mcp-oci"

# Gateway configuration
ENV MCP_GATEWAY_HOST=0.0.0.0 \
    MCP_GATEWAY_PORT=9000 \
    MCP_GATEWAY_PATH=/mcp \
    MCP_GATEWAY_LOG_LEVEL=INFO

EXPOSE 9000

# Health check via the gateway endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:9000/mcp'); assert r.status_code in (200, 405, 406)" || exit 1

ENTRYPOINT ["uv", "run", "oci-mcp-gateway"]
CMD ["--host", "0.0.0.0", "--port", "9000"]
