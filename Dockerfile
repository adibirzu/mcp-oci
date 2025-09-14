# Minimal Dockerfile for MCP OCI servers
FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=on PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install -U pip && pip install -e .[dev]

# Expect OCI config mounted at /root/.oci for root user or set OCI config env vars
# Default command serves IAM; override with other entrypoints as needed
ENV MCP_OCI_LOG_LEVEL=INFO
CMD ["mcp-oci-serve-iam", "--log-level", "INFO"]
