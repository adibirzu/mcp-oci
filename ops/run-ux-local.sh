#!/bin/bash

# Set environment variables for local UX app to connect to containerized observability stack
export OTEL_EXPORTER_OTLP_ENDPOINT="localhost:4317"
export PYROSCOPE_SERVER_ADDRESS="http://localhost:4040"
export GRAFANA_URL="http://localhost:3000"
export PROMETHEUS_URL="http://localhost:9090"
export TEMPO_URL="http://localhost:3200"
export OTEL_SERVICE_NAME="mcp-ux"
export PYROSCOPE_APP_NAME="mcp-ux"

# Enable all observability features
export ENABLE_PYROSCOPE="true"

echo "Starting UX app with observability environment..."
echo "OTEL_EXPORTER_OTLP_ENDPOINT=$OTEL_EXPORTER_OTLP_ENDPOINT"
echo "PYROSCOPE_SERVER_ADDRESS=$PYROSCOPE_SERVER_ADDRESS"

cd "$(dirname "$0")/../"
python -m uvicorn ux.app:app --host 127.0.0.1 --port 8010 --reload