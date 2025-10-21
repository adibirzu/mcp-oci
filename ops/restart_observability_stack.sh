#!/bin/bash
set -euo pipefail

# Detect compose command (Docker CLI v2 uses `docker compose`)
if command -v docker compose >/dev/null 2>&1; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

# If Buildx isn't available, disable BuildKit to avoid TLS/CA issues during pulls on some systems
if ! docker buildx version >/dev/null 2>&1; then
    echo "WARN: Docker Buildx not found; falling back to legacy builder (DOCKER_BUILDKIT=0)"
    export DOCKER_BUILDKIT=0
fi

echo "🔧 MCP-OCI Observability Stack - Complete Restart"
echo "=================================================="

# Stop all containers
echo "🛑 Stopping all observability containers..."
$COMPOSE down --remove-orphans

# Clean up volumes if needed
echo "🧹 Cleaning up old data (optional)..."
read -p "Do you want to clean up all persistent data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $COMPOSE down -v
    echo "✅ Volumes cleaned"
fi

# Rebuild containers
echo "🔨 Rebuilding containers..."
$COMPOSE build --no-cache --pull obs-app

# Start services in order
echo "🚀 Starting observability stack..."

# Start infrastructure services first
echo "  Starting infrastructure services..."
$COMPOSE up -d tempo jaeger pyroscope otel-collector

# Wait for infrastructure to be ready
echo "  Waiting for infrastructure services..."
sleep 10

# Start Prometheus (with host networking)
echo "  Starting Prometheus..."
$COMPOSE up -d prometheus

# Wait for Prometheus
echo "  Waiting for Prometheus..."
sleep 5

# Start Grafana
echo "  Starting Grafana..."
$COMPOSE up -d grafana

# Start obs-app
echo "  Starting obs-app..."
$COMPOSE up -d obs-app

# Wait for all services to be ready
echo "⏳ Waiting for all services to be ready..."
sleep 15

# Verify all services are running
echo "🔍 Verifying service status..."
$COMPOSE ps

echo ""
echo "🧪 Running observability tests..."
python test_observability_server.py || true

echo ""
echo "🌐 Access Points:"
echo "  📊 Grafana: http://localhost:3000 (admin/admin)"
echo "  📈 Prometheus: http://localhost:9090"
echo "  🔍 Jaeger: http://localhost:16686"
echo "  📊 Tempo: http://localhost:3200"
echo "  🔥 Pyroscope: http://localhost:4040"
echo "  🧮 OTLP Collector: http://localhost:8889/metrics"
echo "  📱 MCP UX App: http://localhost:8000"

echo ""
echo "💡 To generate test data:"
echo "  cd ops && python generate_test_data.py --mode metrics"
echo "  cd ops && python generate_test_data.py --mode traces"

echo ""
echo "✅ Observability stack restart complete!"
