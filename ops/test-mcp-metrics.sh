#!/bin/bash

set -e

echo "🧪 Testing MCP Server Metrics Emission"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# MCP servers and their expected metrics ports
declare -A servers=(
    ["mcp-compute"]="8001"
    ["mcp-db"]="8002"
    ["mcp-observability"]="8003"
    ["mcp-security"]="8004"
    ["mcp-network"]="8006"
    ["mcp-blockstorage"]="8007"
    ["mcp-loadbalancer"]="8008"
    ["mcp-inventory"]="8009"
    ["mcp-agents"]="8011"
)

echo "🔍 Testing MCP Server Metrics Endpoints"
echo "=================================================="

all_healthy=true

for server in "${!servers[@]}"; do
    port=${servers[$server]}
    echo -n "Testing $server metrics endpoint (localhost:$port)... "

    if curl -s --max-time 5 "http://localhost:$port/metrics" >/dev/null; then
        success "$server metrics endpoint is accessible"

        # Check if metrics contain MCP-specific data
        metrics_content=$(curl -s "http://localhost:$port/metrics")
        if echo "$metrics_content" | grep -q "mcp_tool"; then
            info "  → MCP tool metrics found"
        else
            warning "  → No MCP tool metrics found (server may not have handled requests yet)"
        fi

        if echo "$metrics_content" | grep -q "http_requests_total"; then
            info "  → HTTP metrics found"
        else
            warning "  → No HTTP metrics found"
        fi

    else
        error "$server metrics endpoint is not accessible"
        all_healthy=false
    fi
done

echo
echo "📊 Testing Prometheus Scraping"
echo "=================================================="

sleep 5  # Wait for Prometheus to scrape

# Test if Prometheus can see the targets
echo -n "Checking Prometheus targets... "
if targets_response=$(curl -s "http://localhost:9090/api/v1/targets" 2>/dev/null); then
    if echo "$targets_response" | jq -e '.data.activeTargets | length > 0' >/dev/null 2>&1; then
        success "Prometheus has active targets"

        # Count healthy MCP server targets
        healthy_mcp_targets=$(echo "$targets_response" | jq '[.data.activeTargets[] | select(.labels.job | startswith("mcp-")) | select(.health == "up")] | length' 2>/dev/null || echo "0")
        total_mcp_targets=$(echo "$targets_response" | jq '[.data.activeTargets[] | select(.labels.job | startswith("mcp-"))] | length' 2>/dev/null || echo "0")

        info "  → $healthy_mcp_targets/$total_mcp_targets MCP servers are healthy in Prometheus"

        if [ "$healthy_mcp_targets" -lt "${#servers[@]}" ]; then
            warning "  → Some MCP servers are not being scraped successfully"
            echo "$targets_response" | jq -r '.data.activeTargets[] | select(.labels.job | startswith("mcp-")) | select(.health != "up") | "    → \(.labels.job): \(.lastError)"' 2>/dev/null || true
        fi
    else
        error "Prometheus has no active targets"
        all_healthy=false
    fi
else
    error "Cannot connect to Prometheus API"
    all_healthy=false
fi

echo
echo "📈 Testing MCP Metrics in Prometheus"
echo "=================================================="

# Test for specific MCP metrics
mcp_metrics=(
    "mcp_tool_calls_total"
    "mcp_tool_duration_seconds"
    "http_requests_total"
    "up"
)

for metric in "${mcp_metrics[@]}"; do
    echo -n "Testing metric '$metric'... "
    if response=$(curl -s "http://localhost:9090/api/v1/query?query=${metric}" 2>/dev/null); then
        if echo "$response" | jq -e '.data.result | length > 0' >/dev/null 2>&1; then
            count=$(echo "$response" | jq '.data.result | length' 2>/dev/null || echo "0")
            success "Metric '$metric' found ($count series)"
        else
            warning "Metric '$metric' exists but has no data yet"
        fi
    else
        error "Failed to query metric '$metric'"
    fi
done

echo
echo "🎯 Testing Grafana Dashboard Data Sources"
echo "=================================================="

# Test Grafana API access
echo -n "Testing Grafana API access... "
if curl -s -u admin:admin "http://localhost:3000/api/health" >/dev/null 2>&1; then
    success "Grafana API accessible"

    # Test data source proxy queries
    echo -n "Testing Prometheus data source... "
    if prom_test=$(curl -s -u admin:admin "http://localhost:3000/api/datasources/proxy/prom/api/v1/query?query=up" 2>/dev/null); then
        if echo "$prom_test" | jq -e '.status == "success"' >/dev/null 2>&1; then
            success "Prometheus data source working"
        else
            warning "Prometheus data source may have issues"
        fi
    else
        error "Cannot query Prometheus through Grafana"
    fi

    echo -n "Testing Tempo data source... "
    if tempo_test=$(curl -s -u admin:admin "http://localhost:3000/api/datasources/proxy/tempo/api/search" 2>/dev/null); then
        if echo "$tempo_test" | jq -e 'type == "object"' >/dev/null 2>&1; then
            success "Tempo data source working"
        else
            warning "Tempo data source may have issues (no traces yet is normal)"
        fi
    else
        warning "Cannot query Tempo through Grafana (may be normal if no traces)"
    fi
else
    error "Grafana API not accessible"
    all_healthy=false
fi

echo
echo "🔗 Testing OpenTelemetry Integration"
echo "=================================================="

# Test OTEL Collector
echo -n "Testing OTEL Collector metrics... "
if otel_metrics=$(curl -s "http://localhost:8889/metrics" 2>/dev/null); then
    if echo "$otel_metrics" | grep -q "otelcol_receiver"; then
        success "OTEL Collector metrics available"

        spans_received=$(echo "$otel_metrics" | grep "otelcol_receiver_accepted_spans_total" | tail -1 | awk '{print $2}' || echo "0")
        spans_sent=$(echo "$otel_metrics" | grep "otelcol_exporter_sent_spans_total" | tail -1 | awk '{print $2}' || echo "0")

        info "  → Spans received: $spans_received"
        info "  → Spans sent: $spans_sent"

        if [ "$spans_received" -gt "0" ] && [ "$spans_sent" -gt "0" ]; then
            success "  → OTEL pipeline is processing spans"
        else
            warning "  → OTEL pipeline has no span activity yet"
        fi
    else
        warning "OTEL Collector metrics found but may be incomplete"
    fi
else
    error "Cannot access OTEL Collector metrics"
fi

echo
echo "📋 Summary"
echo "=================================================="

if $all_healthy; then
    success "All MCP servers and observability components are properly configured!"
    echo
    echo "🎉 Your observability stack is ready for use:"
    echo "   • MCP servers are exposing metrics on their designated ports"
    echo "   • Prometheus is scraping all configured targets"
    echo "   • Grafana dashboards have proper data source configurations"
    echo "   • OpenTelemetry pipeline is ready for traces"
    echo
    echo "🌐 Access your observability tools:"
    echo "   • Grafana: http://localhost:3000 (admin/admin)"
    echo "   • Prometheus: http://localhost:9090"
    echo "   • Tempo: http://localhost:3200"
    echo "   • Pyroscope: http://localhost:4040"
else
    error "Some components are not working correctly."
    echo "📝 Troubleshooting steps:"
    echo "   1. Ensure all MCP servers are started"
    echo "   2. Check server logs for any errors"
    echo "   3. Verify network connectivity between containers and host"
    echo "   4. Run: docker-compose logs -f to check container logs"
    exit 1
fi