#!/bin/bash

# Set environment variables for local UX app to connect to containerized observability stack
export OTEL_EXPORTER_OTLP_ENDPOINT="localhost:4317"
export PYROSCOPE_SERVER_ADDRESS="http://127.0.0.1:4040"
export GRAFANA_URL="http://127.0.0.1:3000"
export PROMETHEUS_URL="http://127.0.0.1:9090"
export TEMPO_URL="http://127.0.0.1:3200"
export JAEGER_URL="http://127.0.0.1:16686"
export OTEL_SERVICE_NAME="mcp-ux"
export PYROSCOPE_APP_NAME="mcp-ux"

# Enable all observability features and force IPv4
export ENABLE_PYROSCOPE="true"
export PYTHONDONTWRITEBYTECODE="1"
export PYTHONUNBUFFERED="1"

# Auto-disable Pyroscope if backend unreachable to avoid client error spam
if [[ "${ENABLE_PYROSCOPE}" =~ ^(1|true|yes|on)$ ]]; then
  if ! curl -fsS "${PYROSCOPE_SERVER_ADDRESS}/" >/dev/null 2>&1; then
    echo "[run-ux-local] Pyroscope not reachable at ${PYROSCOPE_SERVER_ADDRESS}; disabling profiling (ENABLE_PYROSCOPE=false)"
    export ENABLE_PYROSCOPE="false"
  fi
fi

echo "Starting UX app with observability environment..."
echo "OTEL_EXPORTER_OTLP_ENDPOINT=$OTEL_EXPORTER_OTLP_ENDPOINT"
echo "PYROSCOPE_SERVER_ADDRESS=$PYROSCOPE_SERVER_ADDRESS"
echo "ENABLE_PYROSCOPE=$ENABLE_PYROSCOPE"

cd "$(dirname "$0")/../"
python -m uvicorn ux.app:app --host 127.0.0.1 --port 8010 --reload
