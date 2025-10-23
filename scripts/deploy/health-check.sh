#!/usr/bin/env bash
set -uo pipefail  # Removed 'e' to handle errors gracefully

# MCP-OCI Health Check and Monitoring Script
# Performs comprehensive health checks on all MCP services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CHECK_TYPE="${1:-all}"  # all, http, websocket, grpc, specific
TARGET="${2:-localhost}"  # localhost, IP address, or hostname

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

# Service endpoints - Initialize properly for bash 3.x compatibility
declare -A HTTP_ENDPOINTS
HTTP_ENDPOINTS["compute"]="7001"
HTTP_ENDPOINTS["database"]="7002"
HTTP_ENDPOINTS["network"]="7003"
HTTP_ENDPOINTS["iam"]="7004"
HTTP_ENDPOINTS["observability"]="7005"
HTTP_ENDPOINTS["resource"]="7006"
HTTP_ENDPOINTS["cost"]="7007"
HTTP_ENDPOINTS["identity"]="7008"
HTTP_ENDPOINTS["oneagent"]="7009"
HTTP_ENDPOINTS["logging"]="7010"
HTTP_ENDPOINTS["enhanced"]="7011"
HTTP_ENDPOINTS["main"]="8000"

# Health check results
declare -A HEALTH_STATUS
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Check HTTP endpoint
check_http_endpoint() {
    local name=$1
    local port=$2
    local endpoint="http://${TARGET}:${port}/health"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if curl -s -f -o /dev/null -w "%{http_code}" --connect-timeout 5 "$endpoint" | grep -q "200"; then
        HEALTH_STATUS["http_${name}"]="HEALTHY"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        echo -e "  ${GREEN}✓${NC} HTTP ${name} (port ${port}): HEALTHY"

        # Get detailed health info if available
        local health_data=$(curl -s "$endpoint" 2>/dev/null)
        if [[ -n "$health_data" ]]; then
            echo "    Details: $health_data" | head -1
        fi
    else
        HEALTH_STATUS["http_${name}"]="UNHEALTHY"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        echo -e "  ${RED}✗${NC} HTTP ${name} (port ${port}): UNHEALTHY"
    fi
}

# Check WebSocket endpoint
check_websocket() {
    local port=9000
    local endpoint="ws://${TARGET}:${port}"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    log_debug "Checking WebSocket at ${endpoint}..."

    # Use Python to test WebSocket connection
    python3 - <<EOF 2>/dev/null
import asyncio
import websockets
import sys
import json

async def test_websocket():
    try:
        async with websockets.connect("${endpoint}/health", timeout=5) as websocket:
            await websocket.send(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)
            if data.get("type") == "pong":
                sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

asyncio.run(test_websocket())
EOF

    if [[ $? -eq 0 ]]; then
        HEALTH_STATUS["websocket"]="HEALTHY"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        echo -e "  ${GREEN}✓${NC} WebSocket (port ${port}): HEALTHY"
    else
        HEALTH_STATUS["websocket"]="UNHEALTHY"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        echo -e "  ${RED}✗${NC} WebSocket (port ${port}): UNHEALTHY"
    fi
}

# Check gRPC endpoint
check_grpc() {
    local port=50051
    local endpoint="${TARGET}:${port}"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    log_debug "Checking gRPC at ${endpoint}..."

    # Use grpcurl if available, otherwise use basic TCP check
    if command -v grpcurl &> /dev/null; then
        if grpcurl -plaintext -connect-timeout 5 "$endpoint" list &> /dev/null; then
            HEALTH_STATUS["grpc"]="HEALTHY"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            echo -e "  ${GREEN}✓${NC} gRPC (port ${port}): HEALTHY"
        else
            HEALTH_STATUS["grpc"]="UNHEALTHY"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            echo -e "  ${RED}✗${NC} gRPC (port ${port}): UNHEALTHY"
        fi
    else
        # Basic TCP port check
        if nc -z -v -w5 "$TARGET" "$port" &> /dev/null; then
            HEALTH_STATUS["grpc"]="REACHABLE"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            echo -e "  ${YELLOW}?${NC} gRPC (port ${port}): REACHABLE (install grpcurl for detailed check)"
        else
            HEALTH_STATUS["grpc"]="UNREACHABLE"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            echo -e "  ${RED}✗${NC} gRPC (port ${port}): UNREACHABLE"
        fi
    fi
}

# Check metrics endpoint
check_metrics() {
    local port=9090
    local endpoint="http://${TARGET}:${port}/metrics"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if curl -s -f -o /dev/null --connect-timeout 5 "$endpoint"; then
        HEALTH_STATUS["metrics"]="HEALTHY"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        echo -e "  ${GREEN}✓${NC} Metrics (port ${port}): HEALTHY"

        # Get sample metrics
        local metrics=$(curl -s "$endpoint" | grep -E "^mcp_" | head -5)
        if [[ -n "$metrics" ]]; then
            echo "    Sample metrics:"
            echo "$metrics" | sed 's/^/      /'
        fi
    else
        HEALTH_STATUS["metrics"]="UNHEALTHY"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        echo -e "  ${RED}✗${NC} Metrics (port ${port}): UNHEALTHY"
    fi
}

# Check Docker containers
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_debug "Docker not installed, skipping container checks"
        return
    fi

    log_info "Checking Docker containers..."

    local containers=$(docker ps --filter "name=mcp-oci" --format "{{.Names}}:{{.Status}}:{{.State}}" 2>/dev/null)

    if [[ -z "$containers" ]]; then
        echo -e "  ${YELLOW}⚠${NC} No MCP-OCI containers found"
    else
        while IFS=: read -r name status state; do
            TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
            if [[ "$state" == "running" ]]; then
                HEALTH_STATUS["docker_${name}"]="RUNNING"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
                echo -e "  ${GREEN}✓${NC} Container ${name}: ${status}"
            else
                HEALTH_STATUS["docker_${name}"]="NOT_RUNNING"
                FAILED_CHECKS=$((FAILED_CHECKS + 1))
                echo -e "  ${RED}✗${NC} Container ${name}: ${status}"
            fi
        done <<< "$containers"
    fi
}

# Check system resources
check_system_resources() {
    log_info "Checking system resources..."

    # CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 2>/dev/null || echo "N/A")
    if [[ "$cpu_usage" != "N/A" ]]; then
        echo "  CPU Usage: ${cpu_usage}%"
    fi

    # Memory usage
    local mem_info=$(free -h 2>/dev/null | grep "^Mem:" || echo "")
    if [[ -n "$mem_info" ]]; then
        local total=$(echo "$mem_info" | awk '{print $2}')
        local used=$(echo "$mem_info" | awk '{print $3}')
        local available=$(echo "$mem_info" | awk '{print $7}')
        echo "  Memory: Used ${used} / Total ${total} (Available: ${available})"
    fi

    # Disk usage
    local disk_usage=$(df -h / 2>/dev/null | tail -1 | awk '{print $5}' || echo "N/A")
    if [[ "$disk_usage" != "N/A" ]]; then
        echo "  Disk Usage (root): ${disk_usage}"
    fi

    # Network connectivity
    if ping -c 1 -W 2 8.8.8.8 &> /dev/null; then
        echo -e "  Network: ${GREEN}✓${NC} Internet connectivity OK"
    else
        echo -e "  Network: ${YELLOW}⚠${NC} No internet connectivity"
    fi
}

# Check logs for errors
check_logs() {
    log_info "Checking logs for recent errors..."

    local log_dir="$PROJECT_ROOT/logs"
    if [[ -d "$log_dir" ]]; then
        local error_count=$(find "$log_dir" -name "*.log" -mtime -1 -exec grep -i "error\|exception\|critical" {} \; 2>/dev/null | wc -l)
        if [[ $error_count -gt 0 ]]; then
            echo -e "  ${YELLOW}⚠${NC} Found $error_count error(s) in recent logs"
            echo "    Recent errors:"
            find "$log_dir" -name "*.log" -mtime -1 -exec grep -i "error\|exception\|critical" {} \; 2>/dev/null | tail -5 | sed 's/^/      /'
        else
            echo -e "  ${GREEN}✓${NC} No errors in recent logs"
        fi
    else
        log_debug "Log directory not found: $log_dir"
    fi
}

# Perform comprehensive health check
perform_health_check() {
    log_info "Starting MCP-OCI Health Check"
    log_info "Target: ${TARGET}"
    echo ""

    # HTTP endpoints check
    if [[ "$CHECK_TYPE" == "all" || "$CHECK_TYPE" == "http" ]]; then
        log_info "Checking HTTP endpoints..."
        for name in "${!HTTP_ENDPOINTS[@]}"; do
            check_http_endpoint "$name" "${HTTP_ENDPOINTS[$name]}"
        done
        echo ""
    fi

    # WebSocket check
    if [[ "$CHECK_TYPE" == "all" || "$CHECK_TYPE" == "websocket" ]]; then
        log_info "Checking WebSocket endpoint..."
        check_websocket
        echo ""
    fi

    # gRPC check
    if [[ "$CHECK_TYPE" == "all" || "$CHECK_TYPE" == "grpc" ]]; then
        log_info "Checking gRPC endpoint..."
        check_grpc
        echo ""
    fi

    # Metrics check
    if [[ "$CHECK_TYPE" == "all" || "$CHECK_TYPE" == "metrics" ]]; then
        log_info "Checking metrics endpoint..."
        check_metrics
        echo ""
    fi

    # Docker check (only for localhost)
    if [[ "$TARGET" == "localhost" && ("$CHECK_TYPE" == "all" || "$CHECK_TYPE" == "docker") ]]; then
        check_docker
        echo ""
    fi

    # System resources check
    if [[ "$CHECK_TYPE" == "all" || "$CHECK_TYPE" == "system" ]]; then
        check_system_resources
        echo ""
    fi

    # Logs check (only for localhost)
    if [[ "$TARGET" == "localhost" && ("$CHECK_TYPE" == "all" || "$CHECK_TYPE" == "logs") ]]; then
        check_logs
        echo ""
    fi
}

# Generate health report
generate_report() {
    log_info "Health Check Summary"
    echo "================================"
    echo "Total Checks: $TOTAL_CHECKS"
    echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"

    if [[ $TOTAL_CHECKS -gt 0 ]]; then
        local success_rate=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
        echo "Success Rate: ${success_rate}%"

        if [[ $success_rate -eq 100 ]]; then
            echo -e "\n${GREEN}✓ All systems operational${NC}"
        elif [[ $success_rate -ge 80 ]]; then
            echo -e "\n${YELLOW}⚠ Minor issues detected${NC}"
        else
            echo -e "\n${RED}✗ Major issues detected${NC}"
        fi
    fi

    # Save report to file
    local report_file="$PROJECT_ROOT/logs/health-report-$(date +%Y%m%d-%H%M%S).json"
    mkdir -p "$PROJECT_ROOT/logs"

    cat > "$report_file" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "target": "$TARGET",
    "total_checks": $TOTAL_CHECKS,
    "passed": $PASSED_CHECKS,
    "failed": $FAILED_CHECKS,
    "success_rate": ${success_rate:-0},
    "status": $(declare -p HEALTH_STATUS | sed 's/declare -A HEALTH_STATUS=//')
}
EOF

    log_debug "Report saved to: $report_file"
}

# Main execution
main() {
    perform_health_check
    generate_report

    # Exit with error if any checks failed
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        exit 1
    fi
}

# Run main function
main