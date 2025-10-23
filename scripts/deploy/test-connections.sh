#!/bin/bash
set -euo pipefail

# MCP-OCI Connection Test Script
# Tests all connection methods and validates functionality

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_TARGET="${1:-localhost}"
TEST_MODE="${2:-quick}"  # quick, full, stress

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { echo -e "${BLUE}[DEBUG]${NC} $1"; }

# Test results tracking
declare -A TEST_RESULTS
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test HTTP/SSE connection
test_http_sse() {
    local port=$1
    local service=$2

    log_info "Testing HTTP/SSE connection for $service on port $port..."
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    # Test basic HTTP connection
    if curl -s -f "http://${TEST_TARGET}:${port}/health" > /dev/null 2>&1; then
        log_debug "HTTP health check passed"

        # Test SSE streaming
        local test_file="/tmp/sse-test-${port}.txt"
        timeout 5 curl -s -N "http://${TEST_TARGET}:${port}/events" > "$test_file" 2>&1 &
        local curl_pid=$!

        sleep 2
        kill $curl_pid 2>/dev/null || true

        if [[ -s "$test_file" ]]; then
            TEST_RESULTS["http_sse_${service}"]="PASSED"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            echo -e "  ${GREEN}✓${NC} HTTP/SSE $service: Connection successful"
        else
            TEST_RESULTS["http_sse_${service}"]="FAILED"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            echo -e "  ${RED}✗${NC} HTTP/SSE $service: SSE stream failed"
        fi

        rm -f "$test_file"
    else
        TEST_RESULTS["http_sse_${service}"]="FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "  ${RED}✗${NC} HTTP/SSE $service: Connection failed"
    fi
}

# Test WebSocket connection
test_websocket() {
    log_info "Testing WebSocket connection..."
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    # Create Python test script
    cat > /tmp/test-websocket.py <<'EOF'
import asyncio
import websockets
import json
import sys

async def test_websocket():
    try:
        uri = f"ws://{sys.argv[1]}:9000/ws"
        async with websockets.connect(uri, timeout=5) as websocket:
            # Send test message
            test_msg = {"type": "test", "action": "list_instances"}
            await websocket.send(json.dumps(test_msg))

            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)

            if "type" in data:
                print("SUCCESS")
                return 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    return 1

sys.exit(asyncio.run(test_websocket()))
EOF

    if python3 /tmp/test-websocket.py "$TEST_TARGET" 2>/dev/null | grep -q "SUCCESS"; then
        TEST_RESULTS["websocket"]="PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "  ${GREEN}✓${NC} WebSocket: Connection successful"
    else
        TEST_RESULTS["websocket"]="FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "  ${RED}✗${NC} WebSocket: Connection failed"
    fi

    rm -f /tmp/test-websocket.py
}

# Test gRPC connection
test_grpc() {
    log_info "Testing gRPC connection..."
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    # Check if grpcurl is available
    if ! command -v grpcurl &> /dev/null; then
        log_warn "grpcurl not installed, using basic port check"

        if nc -z -v -w5 "$TEST_TARGET" 50051 &> /dev/null; then
            TEST_RESULTS["grpc"]="PARTIAL"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            echo -e "  ${YELLOW}?${NC} gRPC: Port reachable (install grpcurl for full test)"
        else
            TEST_RESULTS["grpc"]="FAILED"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            echo -e "  ${RED}✗${NC} gRPC: Port unreachable"
        fi
    else
        # Test with grpcurl
        if grpcurl -plaintext "${TEST_TARGET}:50051" list &> /dev/null; then
            TEST_RESULTS["grpc"]="PASSED"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            echo -e "  ${GREEN}✓${NC} gRPC: Connection successful"
        else
            TEST_RESULTS["grpc"]="FAILED"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            echo -e "  ${RED}✗${NC} gRPC: Connection failed"
        fi
    fi
}

# Test MCP functionality
test_mcp_functionality() {
    log_info "Testing MCP functionality..."

    # Test compute server - list instances
    log_debug "Testing compute server - list instances..."
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    local response=$(curl -s -X POST "http://${TEST_TARGET}:7001/tools/list_instances" \
        -H "Content-Type: application/json" \
        -d '{"compartment_id": "test"}' 2>/dev/null || echo "")

    if [[ -n "$response" ]]; then
        TEST_RESULTS["mcp_compute"]="PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "  ${GREEN}✓${NC} MCP Compute: Functional"
    else
        TEST_RESULTS["mcp_compute"]="FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "  ${RED}✗${NC} MCP Compute: Not functional"
    fi

    # Test database server - list autonomous databases
    log_debug "Testing database server - list autonomous databases..."
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    response=$(curl -s -X POST "http://${TEST_TARGET}:7002/tools/list_autonomous_databases" \
        -H "Content-Type: application/json" \
        -d '{"compartment_id": "test"}' 2>/dev/null || echo "")

    if [[ -n "$response" ]]; then
        TEST_RESULTS["mcp_database"]="PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "  ${GREEN}✓${NC} MCP Database: Functional"
    else
        TEST_RESULTS["mcp_database"]="FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "  ${RED}✗${NC} MCP Database: Not functional"
    fi

    # Test cost server - get usage
    log_debug "Testing cost server - get usage..."
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    response=$(curl -s -X POST "http://${TEST_TARGET}:7007/tools/get_usage_summary" \
        -H "Content-Type: application/json" \
        -d '{"tenancy_id": "test", "time_usage_started": "2024-01-01"}' 2>/dev/null || echo "")

    if [[ -n "$response" ]]; then
        TEST_RESULTS["mcp_cost"]="PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "  ${GREEN}✓${NC} MCP Cost: Functional"
    else
        TEST_RESULTS["mcp_cost"]="FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "  ${RED}✗${NC} MCP Cost: Not functional"
    fi
}

# Stress test
stress_test() {
    log_info "Running stress test..."

    local concurrent_requests=50
    local test_duration=30

    log_debug "Sending $concurrent_requests concurrent requests for $test_duration seconds..."

    # Create stress test script
    cat > /tmp/stress-test.sh <<EOF
#!/bin/bash
for i in \$(seq 1 $concurrent_requests); do
    while true; do
        curl -s "http://${TEST_TARGET}:8000/health" > /dev/null 2>&1
        sleep 0.1
    done &
done

sleep $test_duration

# Kill all background jobs
jobs -p | xargs kill 2>/dev/null
EOF

    chmod +x /tmp/stress-test.sh

    # Run stress test
    local start_time=$(date +%s)
    /tmp/stress-test.sh > /dev/null 2>&1
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Check if service is still responsive
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if curl -s -f "http://${TEST_TARGET}:8000/health" > /dev/null 2>&1; then
        TEST_RESULTS["stress_test"]="PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "  ${GREEN}✓${NC} Stress Test: Service remained responsive"
    else
        TEST_RESULTS["stress_test"]="FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "  ${RED}✗${NC} Stress Test: Service became unresponsive"
    fi

    rm -f /tmp/stress-test.sh
}

# Performance test
performance_test() {
    log_info "Running performance test..."

    # Measure response time
    local total_time=0
    local num_requests=10

    for i in $(seq 1 $num_requests); do
        local start=$(date +%s%N)
        curl -s "http://${TEST_TARGET}:8000/health" > /dev/null 2>&1
        local end=$(date +%s%N)
        local elapsed=$((($end - $start) / 1000000))  # Convert to milliseconds
        total_time=$((total_time + elapsed))
    done

    local avg_time=$((total_time / num_requests))

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [[ $avg_time -lt 100 ]]; then
        TEST_RESULTS["performance"]="PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "  ${GREEN}✓${NC} Performance: Average response time ${avg_time}ms (< 100ms)"
    elif [[ $avg_time -lt 500 ]]; then
        TEST_RESULTS["performance"]="WARNING"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "  ${YELLOW}⚠${NC} Performance: Average response time ${avg_time}ms (< 500ms)"
    else
        TEST_RESULTS["performance"]="FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "  ${RED}✗${NC} Performance: Average response time ${avg_time}ms (> 500ms)"
    fi
}

# Generate test report
generate_test_report() {
    log_info "Test Results Summary"
    echo "================================"
    echo "Total Tests: $TOTAL_TESTS"
    echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

    if [[ $TOTAL_TESTS -gt 0 ]]; then
        local success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
        echo "Success Rate: ${success_rate}%"

        if [[ $success_rate -eq 100 ]]; then
            echo -e "\n${GREEN}✓ All tests passed!${NC}"
        elif [[ $success_rate -ge 80 ]]; then
            echo -e "\n${YELLOW}⚠ Most tests passed with some failures${NC}"
        else
            echo -e "\n${RED}✗ Multiple test failures detected${NC}"
        fi
    fi

    # Save detailed report
    local report_file="$PROJECT_ROOT/logs/test-report-$(date +%Y%m%d-%H%M%S).json"
    mkdir -p "$PROJECT_ROOT/logs"

    cat > "$report_file" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "target": "$TEST_TARGET",
    "test_mode": "$TEST_MODE",
    "total_tests": $TOTAL_TESTS,
    "passed": $PASSED_TESTS,
    "failed": $FAILED_TESTS,
    "success_rate": ${success_rate:-0},
    "results": $(declare -p TEST_RESULTS | sed 's/declare -A TEST_RESULTS=//')
}
EOF

    log_debug "Detailed report saved to: $report_file"
}

# Main execution
main() {
    log_info "MCP-OCI Connection Test Script"
    log_info "Target: $TEST_TARGET"
    log_info "Test Mode: $TEST_MODE"
    echo ""

    # Quick tests
    if [[ "$TEST_MODE" == "quick" || "$TEST_MODE" == "full" || "$TEST_MODE" == "stress" ]]; then
        log_info "Running basic connection tests..."

        # Test main HTTP endpoints
        test_http_sse 7001 "compute"
        test_http_sse 7002 "database"
        test_http_sse 7007 "cost"
        test_http_sse 8000 "main"

        # Test WebSocket
        test_websocket

        # Test gRPC
        test_grpc

        echo ""
    fi

    # Full tests
    if [[ "$TEST_MODE" == "full" || "$TEST_MODE" == "stress" ]]; then
        log_info "Running functionality tests..."
        test_mcp_functionality
        echo ""

        log_info "Running performance tests..."
        performance_test
        echo ""
    fi

    # Stress tests
    if [[ "$TEST_MODE" == "stress" ]]; then
        log_info "Running stress tests..."
        stress_test
        echo ""
    fi

    # Generate report
    generate_test_report

    # Exit with error if tests failed
    if [[ $FAILED_TESTS -gt 0 ]]; then
        exit 1
    fi
}

# Run main function
main