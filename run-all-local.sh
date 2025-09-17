#!/usr/bin/env bash
# One-script local run for entire demo: observability stack + all MCP servers
# - Detect OS and prefer Colima on macOS (lighter than Docker Desktop)
# - Fall back to Docker Desktop on macOS if requested
# - Handle Docker/Compose/Buildx prerequisites
# - Fix previous Docker build error by using requirements.txt (Dockerfile updated)

set -euo pipefail

NO_DOCKER=false
USE_DOCKER_DESKTOP=false

log()  { printf "\033[1;34m[INFO]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*" 1>&2; }

usage() {
  cat <<EOF
Usage: $0 [--no-docker] [--use-docker-desktop]

Options:
  --no-docker            Run using native binaries (brew services) instead of containers.
  --use-docker-desktop   Force Docker Desktop on macOS (default is Colima).
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-docker) NO_DOCKER=true; shift ;;
    --use-docker-desktop) USE_DOCKER_DESKTOP=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) err "Unknown option: $1"; usage; exit 1 ;;
  esac
done

OS="$(uname -s || echo unknown)"

ensure_homebrew() {
  if [[ "$OS" == "Darwin" ]]; then
    if ! command -v brew >/dev/null 2>&1; then
      log "Homebrew not found. Installing Homebrew..."
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      eval "$(/opt/homebrew/bin/brew shellenv)" || true
      eval "$(/usr/local/bin/brew shellenv)" || true
    fi
  fi
}

ensure_python_poetry() {
  # Python 3.11+
  if ! command -v python3 >/dev/null 2>&1 || ! python3 --version | grep -qE 'Python 3\.1[1-9]'; then
    log "Python 3.11+ not found. Installing..."
    if [[ "$OS" == "Darwin" ]]; then
      brew install python@3.11
    else
      warn "Please install Python 3.11+ for your platform."
    fi
  fi

  # Poetry
  if ! command -v poetry >/dev/null 2>&1; then
    log "Poetry not found. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
    # Ensure Poetry on PATH for current shell
    export PATH="$HOME/.local/bin:$PATH"
  fi

  log "Installing project dependencies with Poetry..."
  poetry install || warn "Poetry install reported issues; continuing."
}

ensure_buildx() {
  if ! docker buildx version >/dev/null 2>&1; then
    if [[ "$OS" == "Darwin" ]]; then
      log "docker buildx not found. Installing via Homebrew..."
      brew install docker-buildx || true
    else
      warn "docker buildx not found. Consider installing buildx for optimal compose builds."
    fi
  fi
}

ensure_compose_cmd() {
  # Prefer plugin `docker compose`, else fall back to classic `docker-compose`
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
  else
    if [[ "$OS" == "Darwin" ]]; then
      log "Docker Compose not found. Installing via Homebrew..."
      brew install docker-compose || true
      if command -v docker-compose >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
      else
        err "Failed to install docker-compose."
        exit 1
      fi
    else
      err "Docker Compose not found. Please install docker compose or docker-compose."
      exit 1
    fi
  fi
}

ensure_docker_desktop_mac() {
  if ! command -v docker >/dev/null 2>&1 || [[ ! -d "/Applications/Docker Desktop.app" ]]; then
    log "Installing Docker Desktop via Homebrew..."
    brew install --cask docker || true
  fi

  if ! docker info >/dev/null 2>&1; then
    log "Starting Docker Desktop..."
    open "/Applications/Docker Desktop.app" || true
    printf "Waiting for Docker Desktop to become ready"
    until docker info >/dev/null 2>&1; do
      printf "."
      sleep 3
    done
    printf "\n"
  fi
  log "Docker Desktop is running."
}

ensure_colima_mac() {
  # Ensure docker CLI present (colima leverages docker client)
  if ! command -v docker >/dev/null 2>&1; then
    log "Installing docker client via Homebrew..."
    brew install docker || true
  fi
  # Install colima if needed
  if ! command -v colima >/dev/null 2>&1; then
    log "Installing Colima..."
    brew install colima || true
  fi
  # Compose fallback if plugin missing handled in ensure_compose_cmd
  # Start Colima if not running
  local status
  status="$(colima status 2>/dev/null || true)"
  if ! echo "$status" | grep -q "Running"; then
    log "Starting Colima (default resources)..."
    # Reasonable defaults; customize with COLIMA_ARGS env if needed
    colima start ${COLIMA_ARGS:-} || {
      err "Failed to start Colima."
      exit 1
    }
  fi
  # Use the colima docker context
  if docker context ls 2>/dev/null | grep -q "colima"; then
    docker context use colima >/dev/null 2>&1 || true
  fi

  # Wait for docker API to be ready
  printf "Waiting for Docker (Colima) to become ready"
  until docker info >/dev/null 2>&1; do
    printf "."
    sleep 2
  done
  printf "\n"
  log "Colima Docker context is ready."
}

ensure_docker_linux() {
  if ! command -v docker >/dev/null 2>&1; then
    err "Docker not found. Please install Docker for your Linux distribution."
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    warn "Docker appears to be stopped. Attempting to start via systemctl..."
    if command -v sudo >/dev/null 2>&1 && command -v systemctl >/dev/null 2>&1; then
      sudo systemctl start docker || true
    fi
  fi
  if ! docker info >/dev/null 2>&1; then
    err "Docker is not running. Please start the Docker daemon."
    exit 1
  fi
}

ensure_container_runtime() {
  if [[ "$NO_DOCKER" == "true" ]]; then
    return
  fi

  case "$OS" in
    Darwin)
      ensure_homebrew
      if [[ "$USE_DOCKER_DESKTOP" == "true" ]]; then
        log "Using Docker Desktop (forced by flag)."
        ensure_docker_desktop_mac
      else
        log "Using Colima for Docker runtime on macOS."
        ensure_colima_mac
      fi
      ;;
    Linux)
      ensure_docker_linux
      ;;
    *)
      err "Unsupported OS: $OS. Please run on macOS or Linux."
      exit 1
      ;;
  esac

  # Buildx and compose
  ensure_buildx
  ensure_compose_cmd

  # Mitigate "Docker Compose is configured to build using Bake, but buildx isn't installed"
  # In case user env forces Bake, explicitly disable CLI build if buildx still absent.
  if ! docker buildx version >/dev/null 2>&1; then
    export COMPOSE_DOCKER_CLI_BUILD=0
    export DOCKER_BUILDKIT=0
  fi
}

launch_native_stack() {
  log "Launching local observability stack with native binaries (--no-docker)..."
  mkdir -p ops/logs
  (cd ops && bash ./run-local.sh) > ops/logs/stack.launch.log 2>&1 &
  log "Observability stack launched (logs in ops/logs/stack.launch.log)."
}

launch_container_stack() {
  log "Starting observability stack (containers)..."
  pushd ops >/dev/null

  # Quiet known Compose noise about 'version' (we removed it already).
  # Build and start in detached mode.
  if [[ "${COMPOSE_DOCKER_CLI_BUILD:-}" == "1" ]] && ! docker buildx version >/dev/null 2>&1; then
    warn "Compose is configured for Bake but buildx is not available; disabling CLI build."
    export COMPOSE_DOCKER_CLI_BUILD=0
    export DOCKER_BUILDKIT=0
  fi

  $COMPOSE_CMD up -d --build

  popd >/dev/null
  log "Observability stack started."
}

launch_mcp_and_ux() {
  log "Starting all MCP servers..."
  scripts/mcp-launchers/start-mcp-server.sh all || warn "MCP server launcher reported issues."

  log "Starting UX app..."
  # Kill previous uvicorn if running on this port
  if lsof -i :8010 >/dev/null 2>&1; then
    warn "Port 8010 in use; attempting to free it."
    pkill -f "uvicorn ux.app:app" || true
    sleep 1
  fi
  uvicorn ux.app:app --reload --port 8010 &
}

main() {
  ensure_homebrew
  ensure_python_poetry

  if [[ "$NO_DOCKER" == "true" ]]; then
    launch_native_stack
  else
    ensure_container_runtime
    launch_container_stack
  fi

  launch_mcp_and_ux

  echo
  echo "All components launched!"
  echo "Access:"
  echo "- Grafana: http://localhost:3000"
  echo "- UX App: http://localhost:8010"
  if [[ "$NO_DOCKER" == "true" ]]; then
    echo "To stop: pkill -f server.py && pkill -f uvicorn && (cd ops && ./run-local.sh stop)"
  else
    echo "To stop containers: (cd ops && $COMPOSE_CMD down) && pkill -f server.py && pkill -f uvicorn"
  fi
}

main "$@"
