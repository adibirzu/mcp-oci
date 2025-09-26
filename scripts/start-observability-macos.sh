#!/bin/bash
#
# macOS Observability Stack Launcher using Colima
#
# This script sets up and runs the complete observability stack for MCP-OCI:
# - Grafana (UI/Dashboarding)
# - Prometheus (Metrics collection)
# - Tempo (Distributed tracing)
# - Pyroscope (Continuous profiling)
# - OpenTelemetry Collector (Data ingestion)
# - Observability App (MCP observability service)
#
# Requirements:
# - macOS with Homebrew
# - Colima (Docker runtime for macOS)
# - Docker Compose
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/ops/docker-compose.yml"
COLIMA_PROFILE="mcp-oci-observability"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."

    # Check macOS
    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_error "This script is designed for macOS only"
        exit 1
    fi

    # Check Homebrew
    if ! command_exists brew; then
        log_error "Homebrew is required. Install from https://brew.sh/"
        exit 1
    fi

    # Check Colima
    if ! command_exists colima; then
        log_warn "Colima not found. Installing..."
        brew install colima
        log_success "Colima installed"
    fi

    # Check Docker
    if ! command_exists docker; then
        log_error "Docker not found. Install Docker Desktop or use 'brew install docker'"
        exit 1
    fi

    # Check Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        log_error "Docker Compose not found. Install with 'brew install docker-compose'"
        exit 1
    fi

    log_success "All requirements satisfied"
}

# Start Colima if not running
start_colima() {
    log_info "Checking Colima status..."

    if ! colima status "$COLIMA_PROFILE" >/dev/null 2>&1; then
        log_warn "Colima profile '$COLIMA_PROFILE' not running. Starting..."

        # Start Colima with appropriate resources for observability stack
        colima start \
            --profile "$COLIMA_PROFILE" \
            --cpu 2 \
            --memory 4 \
            --disk 10 \
            --kubernetes false \
            --network-address \
            --mount-inotify \
            --mount-type=virtiofs

        log_success "Colima started with profile: $COLIMA_PROFILE"
    else
        log_info "Colima profile '$COLIMA_PROFILE' is already running"
    fi

    # Ensure Docker context is set to Colima
    if ! docker context ls | grep -q "colima-$COLIMA_PROFILE"; then
        log_error "Colima Docker context not found. Creating..."
        colima start "$COLIMA_PROFILE" --docker
    fi

    # Switch to Colima context
    docker context use "colima-$COLIMA_PROFILE" >/dev/null 2>&1 || true

    log_success "Docker context set to Colima"
}

# Check if services are running
check_services() {
    log_info "Checking if observability services are running..."

    cd "$PROJECT_ROOT/ops"

    # Check if any services are running
    if docker-compose ps | grep -q "Up"; then
        log_info "Some services are already running. Checking status..."
        docker-compose ps
        return 0
    fi

    log_info "No services currently running"
    return 1
}

# Start all observability services
start_services() {
    log_info "Starting observability services..."

    cd "$PROJECT_ROOT/ops"

    # Use docker-compose (v1) if available, otherwise docker compose (v2)
    if command_exists docker-compose; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi

    log_info "Using: $COMPOSE_CMD"

    # Start services in detached mode
    $COMPOSE_CMD up -d

    log_success "Observability services started"

    # Wait for services to be healthy
    log_info "Waiting for services to be ready..."
    sleep 10

    # Show status
    $COMPOSE_CMD ps
}

# Show access information
show_access_info() {
    log_success "Observability Stack is running!"
    echo ""
    echo "🌐 Access URLs:"
    echo "   📊 Grafana:        http://localhost:3000"
    echo "      └─ Username: admin"
    echo "      └─ Password: admin"
    echo ""
    echo "   📈 Prometheus:     http://localhost:9090"
    echo "   🔍 Tempo:          http://localhost:3200"
    echo "   🔥 Pyroscope:      http://localhost:4040"
    echo "   📡 OTLP Endpoint:  http://localhost:4317"
    echo "   🔧 Observability App: http://localhost:8000"
    echo ""
    echo "📚 Pre-configured Dashboards:"
    echo "   • MCP Monitoring Dashboard (provisioned automatically)"
    echo "   • Default Grafana dashboards"
    echo ""
    echo "🛑 To stop all services:"
    echo "   cd $PROJECT_ROOT/ops && $COMPOSE_CMD down"
    echo ""
    echo "🔄 To restart services:"
    echo "   cd $PROJECT_ROOT/ops && $COMPOSE_CMD restart"
    echo ""
    echo "📊 To view logs:"
    echo "   cd $PROJECT_ROOT/ops && $COMPOSE_CMD logs -f [service-name]"
    echo ""
}

# Stop services
stop_services() {
    log_info "Stopping observability services..."

    cd "$PROJECT_ROOT/ops"

    if command_exists docker-compose; then
        docker-compose down
    else
        docker compose down
    fi

    log_success "Services stopped"
}

# Clean up everything
cleanup() {
    log_warn "Cleaning up..."

    # Stop services
    if [[ -f "$COMPOSE_FILE" ]]; then
        cd "$PROJECT_ROOT/ops"
        if command_exists docker-compose; then
            docker-compose down -v --remove-orphans 2>/dev/null || true
        else
            docker compose down -v --remove-orphans 2>/dev/null || true
        fi
    fi

    # Stop Colima
    if command_exists colima; then
        colima stop "$COLIMA_PROFILE" 2>/dev/null || true
    fi

    log_success "Cleanup completed"
}

# Show usage
usage() {
    echo "macOS Observability Stack Launcher using Colima"
    echo ""
    echo "Usage: $0 [start|stop|status|cleanup|restart]"
    echo ""
    echo "Commands:"
    echo "  start   - Start all observability services (default)"
    echo "  stop    - Stop all services"
    echo "  status  - Show service status"
    echo "  cleanup - Stop services and clean up Colima profile"
    echo "  restart - Restart all services"
    echo ""
    echo "Services included:"
    echo "  • Grafana (Dashboards & Visualization)"
    echo "  • Prometheus (Metrics Collection)"
    echo "  • Tempo (Distributed Tracing)"
    echo "  • Pyroscope (Continuous Profiling)"
    echo "  • OpenTelemetry Collector (Data Ingestion)"
    echo "  • Observability App (MCP Service)"
    echo ""
}

# Main logic
main() {
    local command="${1:-start}"

    case "$command" in
        start)
            log_info "Starting MCP-OCI Observability Stack..."
            check_requirements
            start_colima

            if check_services; then
                log_info "Services are already running"
            else
                start_services
            fi

            show_access_info
            ;;

        stop)
            stop_services
            ;;

        status)
            if check_services; then
                log_info "Checking detailed service status..."
                cd "$PROJECT_ROOT/ops"
                if command_exists docker-compose; then
                    docker-compose ps
                else
                    docker compose ps
                fi
            else
                log_info "No services are running"
            fi
            ;;

        cleanup)
            cleanup
            ;;

        restart)
            log_info "Restarting observability services..."
            cd "$PROJECT_ROOT/ops"
            if command_exists docker-compose; then
                docker-compose restart
            else
                docker compose restart
            fi
            log_success "Services restarted"
            show_access_info
            ;;

        *)
            usage
            exit 1
            ;;
    esac
}

# Handle script interruption
trap cleanup SIGINT SIGTERM

# Run main function
main "$@"
