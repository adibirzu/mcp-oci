#!/bin/bash

set -e

echo "🔧 Starting MCP-OCI Observability Stack"

# Check if Docker is running
if ! docker info &>/dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Navigate to the ops directory
cd "$(dirname "$0")"

echo "🧹 Cleaning up existing containers..."
docker-compose down -v 2>/dev/null || true

echo "🚀 Starting observability stack containers..."
docker-compose up -d

echo "⏳ Waiting for services to become healthy..."

# Wait for Prometheus
echo "  Waiting for Prometheus..."
for i in {1..30}; do
    if curl -s http://localhost:9090/-/ready &>/dev/null; then
        echo "  ✅ Prometheus is ready"
        break
    fi
    sleep 2
done

# Wait for Grafana
echo "  Waiting for Grafana..."
for i in {1..30}; do
    if curl -s http://localhost:3000/api/health &>/dev/null; then
        echo "  ✅ Grafana is ready"
        break
    fi
    sleep 2
done

# Wait for Tempo
echo "  Waiting for Tempo..."
for i in {1..30}; do
    if curl -s http://localhost:3200/ready &>/dev/null; then
        echo "  ✅ Tempo is ready"
        break
    fi
    sleep 2
done

# Wait for Pyroscope
echo "  Waiting for Pyroscope..."
for i in {1..30}; do
    if curl -s http://localhost:4040/ &>/dev/null; then
        echo "  ✅ Pyroscope is ready"
        break
    fi
    sleep 2
done

# Wait for OpenTelemetry Collector
echo "  Waiting for OTEL Collector..."
for i in {1..30}; do
    if nc -z localhost 4317 &>/dev/null; then
        echo "  ✅ OTEL Collector is ready"
        break
    fi
    sleep 2
done

echo "✅ All observability services are ready!"
echo
echo "🌐 Access URLs:"
echo "  - Grafana:    http://localhost:3000 (admin/admin)"
echo "  - Prometheus: http://localhost:9090"
echo "  - Tempo:      http://localhost:3200"
echo "  - Pyroscope:  http://localhost:4040"
echo
echo "💡 Next steps:"
echo "  1. Start MCP servers: ../scripts/mcp-launchers/start-mcp-server.sh start all"
echo "  2. Start UX app: ./run-ux-local.sh"
echo
echo "🔍 To troubleshoot, check logs with: docker-compose logs -f"