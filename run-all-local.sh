#!/bin/bash

# One-script local run for entire demo: observability stack + all MCP servers

set -e

# Function to check and install prerequisites
check_prerequisites() {
    # Check for Homebrew
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    # Check for Python 3.11+
    if ! command -v python3 &> /dev/null || ! python3 --version | grep -q "Python 3.1[1-9]"; then
        echo "Python 3.11+ not found. Installing via Homebrew..."
        brew install python@3.11
    fi

    # Check for Poetry
    if ! command -v poetry &> /dev/null; then
        echo "Poetry not found. Installing..."
        curl -sSL https://install.python-poetry.org | python3 -
    fi

    # Check for Docker only if not in no-docker mode
    if [ "$NO_DOCKER" = false ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS specific checks
            if ! command -v docker &> /dev/null || [ ! -d "/Applications/Docker Desktop.app" ]; then
                echo "Docker Desktop not fully installed. Installing via Homebrew..."
                brew install --cask docker
                echo "Please open Docker Desktop and ensure it's running before proceeding."
                read -p "Press enter when Docker is ready..."
            else
                # Ensure Docker is running
                if ! docker info &> /dev/null; then
                    echo "Docker is installed but not running. Starting Docker..."
                    open '/Applications/Docker Desktop.app'
                    echo "Waiting for Docker to start..."
                    until docker info &> /dev/null; do sleep 5; done
                fi
            fi
        else
            # For non-macOS, assume Docker is handled differently
            if ! command -v docker &> /dev/null; then
                echo "Docker not found. Please install Docker for your platform."
                exit 1
            fi
            if ! docker info &> /dev/null; then
                echo "Docker not running. Please start Docker."
                exit 1
            fi
        fi
    fi

    # Install project dependencies
    poetry install

    # Check for docker compose and install fallback if needed
    if ! docker compose version &> /dev/null; then
        if ! command -v docker-compose &> /dev/null; then
            echo "Docker Compose not found. Installing via Homebrew..."
            brew install docker-compose
        fi
    fi
}

# Check and install prerequisites
# Parse arguments first
NO_DOCKER=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-docker)
            NO_DOCKER=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

check_prerequisites

# Determine compose command (only if not --no-docker)
if [ "$NO_DOCKER" = false ]; then
    COMPOSE_CMD="docker compose"
    if ! $COMPOSE_CMD version &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    fi

    # Launch observability stack
    echo "Starting observability stack..."
    cd ops
    $COMPOSE_CMD up -d --build
    cd ..
else
    echo "Skipping Docker-based observability stack (--no-docker flag detected)."
    echo "Launching MCP servers and UX app natively."
fi

# Launch all MCP servers
echo "Starting all MCP servers..."
scripts/mcp-launchers/start-mcp-server.sh all

# Launch UX app
echo "Starting UX app..."
uvicorn ux.app:app --reload --port 8000 &

echo "All components launched!"
echo "Access:"
echo "- Grafana: http://localhost:3000"
echo "- UX App: http://localhost:8000"
echo "To stop: docker compose down && pkill -f server.py && pkill -f uvicorn"
