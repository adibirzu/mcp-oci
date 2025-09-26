#!/bin/bash

set -e

echo "🚀 Complete MCP-OCI Observability Stack Setup"
echo "=============================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

cd "$(dirname "$0")"

echo
info "Step 1: Starting observability infrastructure..."
./start-observability.sh

echo
info "Step 2: Starting all MCP servers with metrics..."
../scripts/mcp-launchers/start-mcp-server.sh start all

echo
info "Waiting for MCP servers to initialize..."
sleep 10

echo
info "Step 3: Testing observability infrastructure..."
./test-observability.sh

echo
info "Step 4: Testing MCP server metrics emission..."
./test-mcp-metrics.sh

echo
info "Step 5: Testing Pyroscope connectivity..."
./test-pyroscope-connection.sh

echo
echo "🎉 Complete Observability Stack is Ready!"
echo "=========================================="

echo
echo "📊 Your observability stack includes:"
echo "  • All MCP servers instrumented with metrics and tracing"
echo "  • Prometheus scraping metrics from all servers"
echo "  • Grafana dashboards with proper data source configurations"
echo "  • OpenTelemetry pipeline for distributed tracing"
echo "  • Pyroscope for continuous profiling"
echo
echo "🌐 Access your tools:"
echo "  • Grafana Dashboards: http://localhost:3000 (admin/admin)"
echo "    - MCP Overview Dashboard"
echo "    - MCP Servers Overview Dashboard"
echo "  • Prometheus Metrics: http://localhost:9090"
echo "  • Tempo Traces: http://localhost:3200"
echo "  • Pyroscope Profiles: http://localhost:4040"
echo "  • OTEL Collector: http://localhost:8889/metrics"
echo
echo "🔧 Individual MCP server metrics endpoints:"
echo "  • Compute: http://localhost:8001/metrics"
echo "  • DB: http://localhost:8002/metrics"
echo "  • Observability: http://localhost:8003/metrics"
echo "  • Security: http://localhost:8004/metrics"
echo "  • Network: http://localhost:8006/metrics"
echo "  • Blockstorage: http://localhost:8007/metrics"
echo "  • Loadbalancer: http://localhost:8008/metrics"
echo "  • Inventory: http://localhost:8009/metrics"
echo "  • Agents: http://localhost:8011/metrics"
echo
echo "🚀 To start the UX app with full observability:"
echo "  ./run-ux-local.sh"
echo
echo "📚 For more information, see: ./README.md"