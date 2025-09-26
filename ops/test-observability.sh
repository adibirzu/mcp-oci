#!/bin/bash

set -e

echo "🧪 Testing MCP-OCI Observability Stack Integration"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"

    echo -n "Testing $name ($url)... "

    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "^${expected_status}$"; then
        success "$name is responding"
        return 0
    else
        error "$name is not responding"
        return 1
    fi
}

test_metric_availability() {
    local metric_name="$1"
    local endpoint="http://localhost:9090/api/v1/query?query=${metric_name}"

    echo -n "Testing metric '$metric_name'... "

    response=$(curl -s "$endpoint")
    if echo "$response" | jq -e '.data.result | length > 0' >/dev/null 2>&1; then
        success "Metric '$metric_name' is available"
        return 0
    else
        warning "Metric '$metric_name' is not available or has no data"
        return 1
    fi
}

echo "🔍 Testing Service Endpoints"
echo "=================================================="

# Test Prometheus
test_endpoint "Prometheus" "http://localhost:9090/-/ready"

# Test Grafana
test_endpoint "Grafana" "http://localhost:3000/api/health"

# Test Tempo
test_endpoint "Tempo" "http://localhost:3200/ready"

# Test Pyroscope
test_endpoint "Pyroscope" "http://localhost:4040/"

# Test OTEL Collector
test_endpoint "OTEL Collector Metrics" "http://localhost:8889/metrics"

echo
echo "📊 Testing Data Flow"
echo "=================================================="

# Wait a bit for metrics to be scraped
echo "Waiting 10 seconds for metrics collection..."
sleep 10

# Test basic Prometheus metrics
test_metric_availability "up"
test_metric_availability "prometheus_config_last_reload_successful"

# Test OTEL Collector metrics
test_metric_availability "otelcol_receiver_accepted_spans_total"
test_metric_availability "otelcol_exporter_sent_spans_total"

# Test if UX app metrics are being scraped (if running)
if curl -s http://localhost:8010/health >/dev/null 2>&1; then
    success "UX app is running"
    test_metric_availability "http_requests_total"
else
    warning "UX app is not running - start with ./run-ux-local.sh to test full integration"
fi

echo
echo "🔗 Testing Data Source Connectivity"
echo "=================================================="

# Test Grafana data sources
echo -n "Testing Grafana -> Prometheus connection... "
grafana_ds_test=$(curl -s -u admin:admin "http://localhost:3000/api/datasources/proxy/prom/api/v1/query?query=up" | jq -r '.status // "error"')
if [ "$grafana_ds_test" = "success" ]; then
    success "Grafana -> Prometheus connection working"
else
    error "Grafana -> Prometheus connection failed"
fi

echo -n "Testing Grafana -> Tempo connection... "
if curl -s -u admin:admin "http://localhost:3000/api/datasources/proxy/tempo/api/search" | jq -e '.traces' >/dev/null 2>&1; then
    success "Grafana -> Tempo connection working"
else
    warning "Grafana -> Tempo connection may be working but no traces found"
fi

echo
echo "🎯 Integration Summary"
echo "=================================================="

# Check overall health
all_healthy=true

services=("prometheus:9090" "grafana:3000" "tempo:3200" "pyroscope:4040" "otel-collector:8889")
for service in "${services[@]}"; do
    name=${service%:*}
    port=${service#*:}
    if ! nc -z localhost "$port" >/dev/null 2>&1; then
        error "$name service is not accessible"
        all_healthy=false
    fi
done

if $all_healthy; then
    success "All observability services are healthy and accessible"
    echo
    echo "🎉 Observability stack is ready!"
    echo "   • Visit Grafana: http://localhost:3000 (admin/admin)"
    echo "   • View metrics: http://localhost:9090"
    echo "   • Explore traces: http://localhost:3200"
    echo "   • Check profiles: http://localhost:4040"
else
    error "Some services are not healthy. Check docker-compose logs for details."
    exit 1
fi