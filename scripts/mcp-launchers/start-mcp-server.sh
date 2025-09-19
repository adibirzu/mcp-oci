#!/bin/bash
#
# Script to launch/manage MCP servers
#
# Usage:
#   ./start-mcp-server.sh [all | compute | db | network | security | observability | cost | inventory | blockstorage | loadbalancer] [--daemon]
#   ./start-mcp-server.sh status <server>
#   ./start-mcp-server.sh stop <server>
#
# Notes:
# - --daemon keeps one long-lived instance per server (multi-client friendly). Subsequent starts will no-op if already running.
# - Foreground mode (no --daemon) runs the process attached to the terminal (useful for debugging).
# - This script writes PID files under /tmp/mcp-oci-<server>.pid for daemon mode.

set -euo pipefail

# Change to project root
SCRIPT_DIR=$(dirname "$0")
PARENT1=$(dirname "$SCRIPT_DIR")
PARENT2=$(dirname "$PARENT1")
PARENT3=$(dirname "$PARENT2")
cd "$PARENT3"

# Ensure src/ is on PYTHONPATH so servers can import src/mcp_oci_common
export PYTHONPATH="$(pwd)/src:$(pwd):${PYTHONPATH:-}"

PID_DIR="${PID_DIR:-/tmp}"

SERVERS=("compute" "db" "network" "security" "observability" "cost" "inventory" "blockstorage" "loadbalancer")

usage() {
  echo "Usage:"
  echo "  $0 [all | ${SERVERS[*]}] [--daemon]"
  echo "  $0 status <server>"
  echo "  $0 stop <server>"
  exit 1
}

pid_file() {
  local server="$1"
  echo "$PID_DIR/mcp-oci-${server}.pid"
}

is_running() {
  local server="$1"
  local pf
  pf="$(pid_file "$server")"
  if [[ -f "$pf" ]]; then
    local pid
    pid="$(cat "$pf" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && ps -p "$pid" >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

print_status() {
  local server="$1"
  if is_running "$server"; then
    echo "$server is running (PID $(cat "$(pid_file "$server")"))"
    exit 0
  else
    echo "$server is not running"
    exit 3
  fi
}

stop_server() {
  local server="$1"
  local pf
  pf="$(pid_file "$server")"
  if is_running "$server"; then
    local pid
    pid="$(cat "$pf")"
    echo "Stopping $server (PID $pid)..."
    kill "$pid" >/dev/null 2>&1 || true
    # Grace period
    for i in {1..20}; do
      if ps -p "$pid" >/dev/null 2>&1; then
        sleep 0.2
      else
        break
      fi
    done
    if ps -p "$pid" >/dev/null 2>&1; then
      echo "Force killing $server (PID $pid)"
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
    rm -f "$pf"
    echo "$server stopped."
  else
    echo "$server not running."
  fi
}

# Function to launch a single server
launch_server() {
    local server=$1
    local mode=${2:-foreground}  # foreground | daemon

    # OpenTelemetry defaults (can be overridden by environment)
    export OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER:-otlp}"
    export OTEL_METRICS_EXPORTER="${OTEL_METRICS_EXPORTER:-otlp}"
    export OTEL_LOGS_EXPORTER="${OTEL_LOGS_EXPORTER:-otlp}"
    # Prefer gRPC on localhost:4317 for local stack; falls back cleanly if overridden
    export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-http://localhost:4317}"
    export OTEL_EXPORTER_OTLP_PROTOCOL="${OTEL_EXPORTER_OTLP_PROTOCOL:-grpc}"
    # Service metadata for better filtering
    export OTEL_SERVICE_NAME="mcp-oci-$server"
    export FASTMCP_SERVER_NAME="oci-mcp-$server"
    export OTEL_RESOURCE_ATTRIBUTES="${OTEL_RESOURCE_ATTRIBUTES:-deployment.environment=local,service.namespace=mcp-oci,service.version=dev}"

    # Enable controlled mutations for specific servers
    case "$server" in
        compute|db|network|blockstorage|loadbalancer)
            export ALLOW_MUTATIONS="${ALLOW_MUTATIONS:-true}"
            ;;
        *)
            :
            ;;
    esac

    # Enable Pyroscope profiling (non-fatal if backend unavailable)
    export ENABLE_PYROSCOPE="${ENABLE_PYROSCOPE:-true}"
    export PYROSCOPE_APP_NAME="mcp-oci-$server"
    export PYROSCOPE_SERVER_ADDRESS="${PYROSCOPE_SERVER_ADDRESS:-http://pyroscope:4040}"
    export PYROSCOPE_SAMPLE_RATE="${PYROSCOPE_SAMPLE_RATE:-100}"

    local entry="mcp_servers/$server/server.py"
    if [[ ! -f "$entry" ]]; then
      echo "Unknown server or missing entrypoint: $server ($entry not found)"
      exit 2
    fi

    if [[ "$mode" == "daemon" ]]; then
      if is_running "$server"; then
        echo "$server already running (PID $(cat "$(pid_file "$server")")). Skipping."
        return 0
      fi
      echo "Launching $server in daemon mode..."
      # Use poetry run if available, otherwise fallback to python
      if command -v poetry >/dev/null 2>&1; then
        poetry run python "$entry" >/dev/null 2>&1 &
      else
        python "$entry" >/dev/null 2>&1 &
      fi
      local pid=$!
      echo "$pid" > "$(pid_file "$server")"
      echo "$server server launched with PID $pid"
    else
      echo "Launching $server in foreground..."
      if command -v poetry >/dev/null 2>&1; then
        exec poetry run python "$entry"
      else
        exec python "$entry"
      fi
    fi
}

# Parse commands
if [[ $# -lt 1 ]]; then
  usage
fi

cmd="$1"; shift || true

case "$cmd" in
  status)
    [[ $# -eq 1 ]] || usage
    print_status "$1"
    ;;

  stop)
    [[ $# -eq 1 ]] || usage
    stop_server "$1"
    ;;

  all)
    # Start all servers as daemons (no-op if already running)
    for server in "${SERVERS[@]}"; do
      launch_server "$server" "daemon"
    done
    echo "All MCP servers launched (daemon mode). Use '$0 status <server>' to check or '$0 stop <server>' to stop."
    ;;

  compute|db|network|security|observability|cost|inventory|blockstorage|loadbalancer)
    mode="foreground"
    if [[ "${1:-}" == "--daemon" ]]; then
      mode="daemon"
      shift || true
    fi
    launch_server "$cmd" "$mode"
    ;;

  *)
    usage
    ;;
esac

# If we launched anything in foreground, that exec'd and did not return.
# For daemon or management commands, just exit cleanly.
exit 0
