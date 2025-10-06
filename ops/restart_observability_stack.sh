#!/bin/bash
set -e

echo "🔧 MCP-OCI Observability Stack - Complete Restart"
echo "=================================================="

# Stop all containers
echo "🛑 Stopping all observability containers..."
docker-compose down --remove-orphans

# Clean up volumes if needed
echo "🧹 Cleaning up old data (optional)..."
read -p "Do you want to clean up all persistent data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose down -v
    echo "✅ Volumes cleaned"
fi

# Rebuild containers
echo "🔨 Rebuilding containers..."
docker-compose build --no-cache obs-app

# Start services in order
echo "🚀 Starting observability stack..."

# Start infrastructure services first
echo "  Starting infrastructure services..."
docker-compose up -d tempo jaeger pyroscope otel-collector

# Wait for infrastructure to be ready
echo "  Waiting for infrastructure services..."
sleep 10

# Start Prometheus (with host networking)
echo "  Starting Prometheus..."
docker-compose up -d prometheus

# Wait for Prometheus
echo "  Waiting for Prometheus..."
sleep 5

# Start Grafana
echo "  Starting Grafana..."
docker-compose up -d grafana

# Start obs-app
echo "  Starting obs-app..."
docker-compose up -d obs-app

# Wait for all services to be ready
echo "⏳ Waiting for all services to be ready..."
sleep 15

# Verify all services are running
echo "🔍 Verifying service status..."
docker-compose ps

echo ""
echo "🧪 Running observability tests..."
cd ..
python test_observability_e2e.py

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