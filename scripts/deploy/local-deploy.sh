#!/bin/bash
set -euo pipefail

# MCP-OCI Local Deployment Script
# Supports multiple deployment modes and connection options

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOYMENT_MODE="${1:-docker}"  # docker, python, or hybrid
CONNECTION_TYPE="${2:-streamable}"  # streamable, websocket, grpc, all

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi

    # Check Docker
    if [[ "$DEPLOYMENT_MODE" == "docker" || "$DEPLOYMENT_MODE" == "hybrid" ]]; then
        if ! command -v docker &> /dev/null; then
            log_error "Docker is not installed"
            exit 1
        fi

        if ! docker info &> /dev/null; then
            log_error "Docker daemon is not running"
            exit 1
        fi
    fi

    log_info "Prerequisites check passed"
}

# Setup environment
setup_environment() {
    log_info "Setting up environment..."

    cd "$PROJECT_ROOT"

    # Create .env.local if it doesn't exist
    if [[ ! -f .env.local ]]; then
        log_info "Creating .env.local from template..."
        cat > .env.local <<EOF
# Local Development Environment
MCP_ENV=local
MCP_DEBUG=true
MCP_LOG_LEVEL=DEBUG

# Connection Settings
MCP_TRANSPORT=${CONNECTION_TYPE}
MCP_HOST=0.0.0.0

# Streamable HTTP Ports
MCP_PORT_COMPUTE=7001
MCP_PORT_DATABASE=7002
MCP_PORT_NETWORK=7003
MCP_PORT_IAM=7004
MCP_PORT_OBSERVABILITY=7005
MCP_PORT_RESOURCE=7006
MCP_PORT_COST=7007
MCP_PORT_IDENTITY=7008
MCP_PORT_ONEAGENT=7009
MCP_PORT_LOGGING=7010
MCP_PORT_ENHANCED=7011

# Alternative Ports
MCP_PORT_WEBSOCKET=9000
MCP_PORT_GRPC=50051

# OCI Settings (for local testing with credentials)
OCI_CLI_AUTH=api_key
OCI_CONFIG_FILE=~/.oci/config
OCI_CONFIG_PROFILE=DEFAULT

# Performance Settings
MCP_WORKER_COUNT=4
MCP_TIMEOUT=30
MCP_MAX_CONNECTIONS=100

# Monitoring
MCP_ENABLE_METRICS=true
MCP_METRICS_PORT=9090
MCP_ENABLE_TRACING=false
EOF
        log_info "Created .env.local"
    fi

    # Source the environment
    set -a
    source .env.local
    set +a
}

# Deploy with Docker
deploy_docker() {
    log_info "Deploying with Docker..."

    # Create docker-compose.local.yml
    cat > "$PROJECT_ROOT/docker-compose.local.yml" <<EOF
version: "3.9"

services:
  mcp-oci:
    build:
      context: .
      dockerfile: Dockerfile
    image: mcp-oci:local
    container_name: mcp-oci-local
    restart: unless-stopped
    env_file:
      - .env.local
    ports:
      # Streamable HTTP ports
      - "7001:7001"
      - "7002:7002"
      - "7003:7003"
      - "7004:7004"
      - "7005:7005"
      - "7006:7006"
      - "7007:7007"
      - "7008:7008"
      - "7009:7009"
      - "7010:7010"
      - "7011:7011"
      # Main HTTP ports
      - "8000:8000"
      - "8001:8001"
      - "8002:8002"
      - "8003:8003"
      - "8004:8004"
      - "8005:8005"
      - "8006:8006"
      - "8007:8007"
      - "8008:8008"
      - "8009:8009"
      - "8010:8010"
      - "8011:8011"
      # WebSocket port
      - "9000:9000"
      # gRPC port
      - "50051:50051"
      # Metrics port
      - "9090:9090"
    volumes:
      - ./logs:/app/logs
      - ~/.oci:/root/.oci:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - mcp-network

networks:
  mcp-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
EOF

    # Build and start
    log_info "Building Docker image..."
    docker-compose -f docker-compose.local.yml build

    log_info "Starting Docker container..."
    docker-compose -f docker-compose.local.yml up -d

    # Wait for health check
    log_info "Waiting for service to be healthy..."
    for i in {1..30}; do
        if docker-compose -f docker-compose.local.yml ps | grep -q "healthy"; then
            log_info "Service is healthy!"
            break
        fi
        sleep 2
    done
}

# Deploy with Python
deploy_python() {
    log_info "Deploying with Python..."

    cd "$PROJECT_ROOT"

    # Create virtual environment if it doesn't exist
    if [[ ! -d .venv ]]; then
        log_info "Creating virtual environment..."
        python3 -m venv .venv
    fi

    # Activate virtual environment
    source .venv/bin/activate

    # Install dependencies
    log_info "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt

    # Create startup script
    cat > "$PROJECT_ROOT/start-local.py" <<EOF
#!/usr/bin/env python3
"""Local MCP Server Startup Script"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_servers.orchestrator import OrchestratorServer

async def main():
    """Start all MCP servers based on configuration"""

    # Configure based on CONNECTION_TYPE
    connection_type = os.getenv("MCP_TRANSPORT", "streamable")

    print(f"Starting MCP servers with {connection_type} transport...")

    # Initialize orchestrator
    orchestrator = OrchestratorServer()

    # Start servers based on connection type
    if connection_type == "all":
        await orchestrator.start_all()
    else:
        await orchestrator.start(connection_type)

    print("MCP servers started successfully")

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nShutting down MCP servers...")
        await orchestrator.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
EOF

    # Start in background
    log_info "Starting MCP servers..."
    nohup python start-local.py > logs/mcp-local.log 2>&1 &
    echo $! > /tmp/mcp-oci-local.pid

    log_info "MCP servers started with PID: $(cat /tmp/mcp-oci-local.pid)"
}

# Deploy hybrid mode
deploy_hybrid() {
    log_info "Deploying in hybrid mode..."

    # Start Docker for main services
    deploy_docker

    # Start Python for additional services
    deploy_python
}

# Check deployment status
check_status() {
    log_info "Checking deployment status..."

    if [[ "$DEPLOYMENT_MODE" == "docker" || "$DEPLOYMENT_MODE" == "hybrid" ]]; then
        log_info "Docker containers:"
        docker ps --filter "name=mcp-oci" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    fi

    if [[ "$DEPLOYMENT_MODE" == "python" || "$DEPLOYMENT_MODE" == "hybrid" ]]; then
        if [[ -f /tmp/mcp-oci-local.pid ]]; then
            PID=$(cat /tmp/mcp-oci-local.pid)
            if ps -p $PID > /dev/null; then
                log_info "Python process running with PID: $PID"
            else
                log_warn "Python process not running"
            fi
        fi
    fi

    # Test connections
    log_info "Testing connections..."

    # Test HTTP health endpoint
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
        log_info "HTTP health check: OK"
    else
        log_warn "HTTP health check: Failed"
    fi

    # Show available endpoints
    log_info "Available endpoints:"
    echo "  - HTTP (Streamable): http://localhost:7001-7011, 8000-8011"
    echo "  - WebSocket: ws://localhost:9000"
    echo "  - gRPC: localhost:50051"
    echo "  - Metrics: http://localhost:9090/metrics"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up previous deployments..."

    # Stop Docker containers
    if docker ps -q --filter "name=mcp-oci" | grep -q .; then
        log_info "Stopping Docker containers..."
        docker-compose -f docker-compose.local.yml down 2>/dev/null || true
    fi

    # Stop Python processes
    if [[ -f /tmp/mcp-oci-local.pid ]]; then
        PID=$(cat /tmp/mcp-oci-local.pid)
        if ps -p $PID > /dev/null; then
            log_info "Stopping Python process..."
            kill $PID 2>/dev/null || true
        fi
        rm -f /tmp/mcp-oci-local.pid
    fi
}

# Main execution
main() {
    log_info "MCP-OCI Local Deployment Script"
    log_info "Deployment Mode: $DEPLOYMENT_MODE"
    log_info "Connection Type: $CONNECTION_TYPE"

    # Check prerequisites
    check_prerequisites

    # Cleanup previous deployments
    cleanup

    # Setup environment
    setup_environment

    # Deploy based on mode
    case "$DEPLOYMENT_MODE" in
        docker)
            deploy_docker
            ;;
        python)
            deploy_python
            ;;
        hybrid)
            deploy_hybrid
            ;;
        *)
            log_error "Invalid deployment mode: $DEPLOYMENT_MODE"
            echo "Usage: $0 [docker|python|hybrid] [streamable|websocket|grpc|all]"
            exit 1
            ;;
    esac

    # Check status
    check_status

    log_info "Deployment complete!"
}

# Run main function
main