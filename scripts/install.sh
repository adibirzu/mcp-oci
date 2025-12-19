#!/usr/bin/env bash
# Simple installer for MCP-OCI: installs prerequisites, sets up Python env, verifies OCI config,
# builds Docker image, then starts Observability stack and MCP servers.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Load .env.local if it exists (before any other operations)
if [[ -f "$REPO_ROOT/.env.local" ]]; then
  set -a
  source "$REPO_ROOT/.env.local"
  set +a
  say "Loaded environment from .env.local"
fi

say() { echo -e "==> $*"; }
warn() { echo -e "WARNING: $*" >&2; }
die() { echo -e "ERROR: $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command '$1' not found. Please install it and re-run."
}

# Detect OS
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"

# Choose python
choose_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi
  die "No python interpreter found (python3/python)"
}

ensure_docker() {
  if command -v docker >/dev/null 2>&1; then
    # Verify Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
      warn "Docker CLI found but the Docker daemon is not running."
      case "$OS" in
        darwin)
          die "Start Docker Desktop (Applications -> Docker) and re-run ./scripts/install.sh"
          ;;
        linux)
          warn "Attempting to start Docker service (requires sudo) ..."
          if command -v systemctl >/dev/null 2>&1; then
            sudo systemctl start docker || true
          fi
          if ! docker info >/dev/null 2>&1; then
            die "Docker service not running. Start it (e.g., 'sudo systemctl start docker') and re-run this installer."
          fi
          ;;
        *)
          die "Start Docker and re-run the installer."
          ;;
      esac
    fi
    return 0
  fi
  warn "Docker not found. Attempting to guide installation."
  case "$OS" in
    darwin)
      if command -v brew >/dev/null 2>&1; then
        say "Installing Docker Desktop via Homebrew Cask (requires user session GUI)..."
        brew install --cask docker || true
        say "Please launch Docker Desktop and ensure it is running, then re-run this installer."
      else
        warn "Homebrew not found. Install Docker Desktop from: https://docs.docker.com/desktop/install/mac-install/"
      fi
      exit 1
      ;;
    linux)
      if command -v apt-get >/dev/null 2>&1; then
        say "Installing Docker (apt-get, requires sudo)..."
        sudo apt-get update
        sudo apt-get install -y docker.io
        sudo usermod -aG docker "$USER" || true
        warn "You may need to log out/in for docker group permissions to take effect."
      elif command -v dnf >/dev/null 2>&1; then
        say "Installing Docker (dnf, requires sudo)..."
        sudo dnf install -y docker
        sudo systemctl enable --now docker
      else
        warn "Unsupported package manager. Install Docker from: https://docs.docker.com/engine/install/"
        exit 1
      fi
      ;;
    *)
      warn "Unrecognized OS '$OS'. Please install Docker manually: https://docs.docker.com/engine/install/"
      exit 1
      ;;
  esac
}

ensure_docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    export COMPOSE_BIN="docker compose"
    return 0
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    export COMPOSE_BIN="docker-compose"
    return 0
  fi
  warn "Docker Compose plugin not found. Installing compose v2 requires Docker >= 20.10."
  die "Install Docker Compose and re-run. See: https://docs.docker.com/compose/install/"
}

ensure_oci_cli() {
  if command -v oci >/dev/null 2>&1; then
    return 0
  fi
  say "OCI CLI not found. Installing into Python virtualenv (pip install oci-cli)..."
  # We will install into the active venv (created below). If venv not yet created, defer this.
  export INSTALL_OCI_CLI_WITH_PIP="1"
}

ensure_python_env() {
  local PY_BIN
  PY_BIN="$(choose_python)"
  say "Using Python: $PY_BIN"
  if [ ! -d .venv ]; then
    "$PY_BIN" -m venv .venv
  fi
  # shellcheck disable=SC1091
  . .venv/bin/activate
  pip install -U pip
  # Install project with extras needed for OCI servers
  say "Installing project dependencies (editable) ..."
  pip install -e .[oci]
  if [[ "${INSTALL_OCI_CLI_WITH_PIP:-}" == "1" ]]; then
    say "Installing OCI CLI via pip ..."
    pip install oci-cli
  fi
}

ensure_venv_symlink() {
  if [[ ! -d .venv ]]; then
    warn "Skipping .venv311 creation; Python virtualenv missing"
    return 0
  fi
  if [[ -e .venv311 && ! -L .venv311 ]]; then
    rm -rf .venv311
  fi
  ln -sfn .venv .venv311
  say "Ensured .venv311 links to .venv for stdio discovery"
}

verify_oci_config() {
  say "Verifying OCI credentials/config ..."
  # Accept either ~/.oci/config or Environment/Instance/Resource Principals hints.
  local OCI_CFG="${HOME}/.oci/config"
  if [ -f "$OCI_CFG" ]; then
    say "Found OCI CLI config at $OCI_CFG"
    return 0
  fi
  # If running in OCI with resource principals, user may not have config; allow if explicit env provided
  if [[ -n "${OCI_PROFILE:-}" || -n "${OCI_REGION:-}" || -n "${TENANCY_OCID:-}" ]]; then
    warn "No ~/.oci/config, but OCI env variables are present. Proceeding."
    return 0
  fi

  echo
  echo "No OCI CLI configuration detected at ${OCI_CFG}."
  read -r -p "Would you like to run 'oci setup config' now? [Y/n] " ans
  ans=${ans:-Y}
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    # shellcheck disable=SC1091
    . .venv/bin/activate
    oci setup config || true
    if [ -f "$OCI_CFG" ]; then
      say "OCI config created at ${OCI_CFG}"
      return 0
    fi
    die "OCI config was not created. Re-run 'oci setup config' manually and then re-run ./scripts/install.sh"
  else
    cat <<MSG
You need to configure OCI credentials before continuing.

Run:
  1) source .venv/bin/activate
  2) oci setup config

Then re-run:
  ./scripts/install.sh
MSG
    exit 2
  fi
}

build_mcp_image() {
  say "Building Docker image for MCP servers (mcp-oci:latest) ..."
  docker build -t mcp-oci:latest .
}

start_observability() {
  say "Starting Observability stack (Grafana, Prometheus, Tempo, Pyroscope, OTEL Collector) ..."
  pushd ops >/dev/null
  $COMPOSE_BIN up -d
  popd >/dev/null

  say "Observability endpoints:"
  echo "  Grafana:     http://localhost:3000 (admin/admin)"
  echo "  Prometheus:  http://localhost:9090"
  echo "  Tempo:       http://localhost:3200"
  echo "  Pyroscope:   http://localhost:4040"
  echo "  Jaeger:      http://localhost:16686"
}

run_tenancy_discovery() {
  say "Running tenancy discovery..."
  # shellcheck disable=SC1091
  . .venv/bin/activate
  python scripts/init_tenancy_discovery.py || {
    warn "Tenancy discovery failed, but continuing with server startup..."
  }
  say "Tenancy discovery completed"
}

start_mcp_servers() {
  say "Starting MCP servers (daemon) ..."
  # shellcheck disable=SC1091
  . .venv/bin/activate
  scripts/mcp-launchers/start-mcp-server.sh all --daemon || {
    warn "Failed to start MCP servers with launcher. Check logs or start individually."
    exit 3
  }
  say "MCP servers launched. Health check summary:"
  # shellcheck disable=SC1091
  . .venv/bin/activate
  python ops/smoke_test_mcp.py || true
  say "MCP doctor summary written to ops/MCP_HEALTH.json"
}

post_install_summary() {
  say "Installation complete."
  echo
  echo "Next steps:"
  echo "  - Ensure Docker is running and healthy."
  echo "  - To view dashboards:"
  echo "      Grafana:     http://localhost:3000 (admin/admin)"
  echo "      Prometheus:  http://localhost:9090"
  echo "      Tempo:       http://localhost:3200"
  echo "      Pyroscope:   http://localhost:4040"
  echo "      Jaeger:      http://localhost:16686"
  echo "  - MCP health summary: ops/MCP_HEALTH.json"
  echo
  echo "Environment tips:"
  echo "  export OCI_PROFILE=DEFAULT"
  echo "  export OCI_REGION=eu-frankfurt-1"
  echo "  export COMPARTMENT_OCID=ocid1.compartment.oc1..xxxxx (optional default scope)"
  echo "  export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317"
  echo
  echo "Docker-based MCP config is available at: mcp-docker.json"
}

main() {
  say "MCP-OCI installer started"
  ensure_docker
  ensure_docker_compose
  ensure_oci_cli
  ensure_python_env
  ensure_venv_symlink
  verify_oci_config
  run_tenancy_discovery
  build_mcp_image
  start_observability
  start_mcp_servers
  post_install_summary
}

main "$@"
