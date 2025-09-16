#!/bin/bash

# Script to run observability stack locally without Docker
# Assumes binaries are downloaded in ops/bin/ (see README for setup)

# Set environment variables
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Start Prometheus
echo "Starting Prometheus..."
./bin/prometheus --config.file=../prometheus/prometheus.yml --web.listen-address=:9090 &
PROM_PID=$!

# Start Tempo
echo "Starting Tempo..."
./bin/tempo -config.file=../tempo/tempo.yaml &
TEMPO_PID=$!

# Start OTEL Collector
echo "Starting OTEL Collector..."
./bin/otelcol --config=../otel/otel-collector.yaml &
OTEL_PID=$!

# Start Grafana
echo "Starting Grafana..."
./bin/grafana-server --config=../grafana/grafana.ini --homepath=./bin/grafana &
GRAFANA_PID=$!

# Start obs-app
echo "Starting obs-app..."
cd ../../obs_app
uvicorn app:app --host 0.0.0.0 --port 8000 &
OBS_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Stopping services..."
    kill $PROM_PID $TEMPO_PID $OTEL_PID $GRAFANA_PID $OBS_PID
}

trap cleanup EXIT

# Wait for services
sleep 5

echo "Services started:"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000 (admin/admin)"
echo "- Tempo: http://localhost:3200"
echo "- OTEL Collector: (listening on 4318)"
echo "- obs-app: http://localhost:8000"

# Keep script running
wait
