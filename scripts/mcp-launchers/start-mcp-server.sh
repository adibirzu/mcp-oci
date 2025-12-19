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
# Project root is two levels up from this script (mcp-oci)
cd "$PARENT2"
# Ensure globbing returns empty instead of a literal when there are no matches
shopt -s nullglob

# Load .env.local if it exists (before any other operations)
if [[ -f "$PARENT2/.env.local" ]]; then
  set -a
  source "$PARENT2/.env.local"
  set +a
  echo "[INFO] Loaded environment from .env.local"
fi

# Ensure src/ is on PYTHONPATH so servers can import src/mcp_oci_common
export PYTHONPATH="$(pwd)/src:$(pwd):${PYTHONPATH:-}"

# Run tenancy discovery before starting servers
run_tenancy_discovery() {
  if [[ -f "scripts/init_tenancy_discovery.py" ]]; then
    echo "[INFO] Running tenancy discovery..."
    python3 scripts/init_tenancy_discovery.py >/dev/null 2>&1 || {
      echo "[WARN] Tenancy discovery failed, continuing anyway..."
    }
  fi
}

PID_DIR="${PID_DIR:-/tmp}"

# Dynamically discover servers from mcp_servers/ directories
declare -a SERVERS=()
for dir in mcp_servers/*; do
  if [[ -f "$dir/server.py" ]]; then
    SERVERS+=("$(basename "$dir")")
  fi
done

usage() {
  echo "Usage:"
  echo "  $0 [all | ${SERVERS[*]:-}] [--daemon]"
  echo "  $0 status <server>"
  echo "  $0 stop <server>"
  exit 1
}

pid_file() {
  local server="$1"
  echo "$PID_DIR/mcp-oci-${server}.pid"
}

normalize_server() {
  local name="$1"
  # Map aliases like 'mcp-observability' -> 'observability'
  if [[ "$name" == mcp-* ]]; then
    echo "${name#mcp-}"
  else
    echo "$name"
  fi
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
  local s
  s="$(normalize_server "$server")"
  if is_running "$s"; then
    echo "$s is running (PID $(cat "$(pid_file "$s")"))"
    exit 0
  else
    echo "$s is not running"
    exit 3
  fi
}

stop_server() {
  local server="$1"
  local s
  s="$(normalize_server "$server")"
  local pf
  pf="$(pid_file "$s")"
  if is_running "$s"; then
    local pid
    pid="$(cat "$pf")"
    echo "Stopping $s (PID $pid)..."
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
      echo "Force killing $s (PID $pid)"
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
    rm -f "$pf"
    echo "$s stopped."
  else
    echo "$s not running."
  fi
}

# Function to launch a single server
launch_server() {
    local server=$1
    local mode=${2:-foreground}  # foreground | daemon
    
    # Run tenancy discovery before starting server (only once per session)
    if [[ -z "${TENANCY_DISCOVERY_RUN:-}" ]]; then
      run_tenancy_discovery
      export TENANCY_DISCOVERY_RUN="1"
    fi

    # OpenTelemetry defaults - prioritize OCI APM over local collector
    export OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER:-otlp}"
    export OTEL_METRICS_EXPORTER="${OTEL_METRICS_EXPORTER:-otlp}"
    export OTEL_LOGS_EXPORTER="${OTEL_LOGS_EXPORTER:-otlp}"
    
    # OCI APM configuration takes precedence if available
    if [[ -n "${OCI_APM_ENDPOINT:-}" && -n "${OCI_APM_PRIVATE_DATA_KEY:-}" ]]; then
      # Use OCI APM endpoint (HTTP/HTTPS)
      export OTEL_EXPORTER_OTLP_ENDPOINT="${OCI_APM_ENDPOINT}"
      export OTEL_EXPORTER_OTLP_PROTOCOL="${OTEL_EXPORTER_OTLP_PROTOCOL:-http/protobuf}"
      export OTEL_EXPORTER_OTLP_HEADERS="Authorization=dataKey ${OCI_APM_PRIVATE_DATA_KEY}"
      # Disable local OTEL collector when OCI APM is configured
      export OTEL_DISABLE_LOCAL="${OTEL_DISABLE_LOCAL:-true}"
      export OTEL_TRACING_ENABLED="${OTEL_TRACING_ENABLED:-true}"
    else
      # Fallback to local collector (for development)
      # NOTE: gRPC exporters expect 'host:port' without http:// prefix
      export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-localhost:4317}"
      export OTEL_EXPORTER_OTLP_PROTOCOL="${OTEL_EXPORTER_OTLP_PROTOCOL:-grpc}"
      # Disable local OTEL if explicitly requested
      if [[ "${OTEL_DISABLE_LOCAL:-false}" == "true" ]]; then
        export OTEL_TRACING_ENABLED="false"
      fi
    fi
    # Service metadata for better filtering
    export OTEL_SERVICE_NAME="mcp-oci-$server"
    export FASTMCP_SERVER_NAME="oci-mcp-$server"
    export OTEL_RESOURCE_ATTRIBUTES="${OTEL_RESOURCE_ATTRIBUTES:-deployment.environment=local,service.namespace=mcp-oci,service.version=dev}"

    # Enable privacy masking by default (can be overridden by env)
    export MCP_OCI_PRIVACY="${MCP_OCI_PRIVACY:-true}"

	    # Log Analytics namespace is tenancy-specific; do not set defaults here.
	    # Set LA_NAMESPACE explicitly (e.g., in .env.local) if needed.

    # Enable controlled mutations for specific servers
    case "$server" in
	        compute|db|network|blockstorage|loadbalancer|objectstorage)
            export ALLOW_MUTATIONS="${ALLOW_MUTATIONS:-true}"
            ;;
        *)
            :
            ;;
    esac

    # Enable Pyroscope profiling (non-fatal if backend unavailable)
    # Default disabled to avoid noisy connection errors when no backend is present (e.g., OKE, CI)
    export ENABLE_PYROSCOPE="${ENABLE_PYROSCOPE:-false}"
    export PYROSCOPE_APP_NAME="mcp-oci-$server"
    # Use IPv4 loopback by default for local docker-compose; override in k8s/CI via env
    export PYROSCOPE_SERVER_ADDRESS="${PYROSCOPE_SERVER_ADDRESS:-http://127.0.0.1:4040}"
    export PYROSCOPE_SAMPLE_RATE="${PYROSCOPE_SAMPLE_RATE:-100}"
    # Auto-disable Pyroscope if backend is unreachable to avoid client spam
    if [[ "${ENABLE_PYROSCOPE}" =~ ^(1|true|yes|on)$ ]]; then
      if ! curl -fsS "${PYROSCOPE_SERVER_ADDRESS}/" >/dev/null 2>&1; then
        echo "Pyroscope not reachable at ${PYROSCOPE_SERVER_ADDRESS}; disabling profiling for ${server}." >&2
        export ENABLE_PYROSCOPE="false"
      fi
    fi

    # Ensure metrics port aligns with UX expectations
	    case "$server" in
	      compute)       export METRICS_PORT="${METRICS_PORT:-8001}" ;;
	      db)            export METRICS_PORT="${METRICS_PORT:-10002}" ;;
	      observability) export METRICS_PORT="${METRICS_PORT:-8003}" ;;
	      security)      export METRICS_PORT="${METRICS_PORT:-8004}" ;;
	      cost)          export METRICS_PORT="${METRICS_PORT:-8005}" ;;
	      network)       export METRICS_PORT="${METRICS_PORT:-8006}" ;;
	      blockstorage)  export METRICS_PORT="${METRICS_PORT:-8007}" ;;
	      loadbalancer)  export METRICS_PORT="${METRICS_PORT:-8008}" ;;
	      inventory)     export METRICS_PORT="${METRICS_PORT:-8009}" ;;
	      unified)       export METRICS_PORT="${METRICS_PORT:-8010}" ;;
	      agents)        export METRICS_PORT="${METRICS_PORT:-8011}" ;;
	      objectstorage) export METRICS_PORT="${METRICS_PORT:-8012}" ;;
	      *)            : ;;
	    esac

    # Default MCP transport configuration (overridable by env or flags)
    # In daemon mode default to network transport to avoid blocking on stdio
    if [[ "$mode" == "daemon" && -z "${MCP_TRANSPORT:-}" ]]; then
      export MCP_TRANSPORT="http"
    fi
    export MCP_TRANSPORT="${MCP_TRANSPORT:-stdio}"   # stdio | http | sse | streamable-http
    export MCP_HOST="${MCP_HOST:-127.0.0.1}"
    
    # Compute default MCP_PORT:
    # - For network transports use per-service stable ports (avoid clashing with Prometheus METRICS_PORT)
    # - For stdio, keep legacy behavior (MCP_PORT follows METRICS_PORT) if unset
    if [[ "${MCP_TRANSPORT}" != "stdio" ]]; then
      if [[ -z "${MCP_PORT:-}" ]]; then
	        case "$server" in
	          compute)       export MCP_PORT="${MCP_PORT_COMPUTE:-7001}" ;;
	          db)            export MCP_PORT="${MCP_PORT_DB:-7002}" ;;
	          observability) export MCP_PORT="${MCP_PORT_OBSERVABILITY:-7003}" ;;
	          security)      export MCP_PORT="${MCP_PORT_SECURITY:-7004}" ;;
	          cost)          export MCP_PORT="${MCP_PORT_COST:-7005}" ;;
	          network)       export MCP_PORT="${MCP_PORT_NETWORK:-7006}" ;;
	          blockstorage)  export MCP_PORT="${MCP_PORT_BLOCKSTORAGE:-7007}" ;;
	          loadbalancer)  export MCP_PORT="${MCP_PORT_LOADBALANCER:-7008}" ;;
	          inventory)     export MCP_PORT="${MCP_PORT_INVENTORY:-7009}" ;;
	          unified)       export MCP_PORT="${MCP_PORT_UNIFIED:-7010}" ;;
	          agents)        export MCP_PORT="${MCP_PORT_AGENTS:-7011}" ;;
	          objectstorage) export MCP_PORT="${MCP_PORT_OBJECTSTORAGE:-7012}" ;;
	          *)             export MCP_PORT="${MCP_PORT_DEFAULT:-7099}" ;;
	        esac
	      fi
      # Avoid metrics collision: if METRICS_PORT equals MCP_PORT, disable metrics before Python starts
      if [[ -n "${METRICS_PORT:-}" && "${METRICS_PORT}" == "${MCP_PORT}" ]]; then
        export METRICS_PORT="-1"
      fi
    else
      # stdio mode fallback: if not provided, default control port to METRICS_PORT to keep ports predictable
      if [[ -z "${MCP_PORT:-}" ]]; then
        export MCP_PORT="${METRICS_PORT:-8000}"
      fi
    fi

    local entry="mcp_servers/$server/server.py"
    if [[ ! -f "$entry" ]]; then
      echo "Unknown server or missing entrypoint: $server ($entry not found)" >&2
      exit 2
    fi

    if [[ "$mode" == "daemon" ]]; then
      if is_running "$server"; then
        echo "$server already running (PID $(cat "$(pid_file "$server")")). Skipping."
        return 0
      fi
      echo "Launching $server in daemon mode..." >&2
      # Use poetry run if available, otherwise fallback to python
      mkdir -p logs
      local logfile="logs/mcp-${server}.log"
      if command -v poetry >/dev/null 2>&1; then
        nohup poetry run python "$entry" >>"$logfile" 2>&1 &
      else
        PY_BIN="$( [ -x ".venv/bin/python" ] && echo ".venv/bin/python" || command -v python3 || command -v python )"
        nohup "$PY_BIN" "$entry" >>"$logfile" 2>&1 &
      fi
      local pid=$!
      echo "$pid" > "$(pid_file "$server")"
      echo "$server server launched with PID $pid (logs: $logfile)" >&2
    else
      echo "Launching $server in foreground..." >&2
      if command -v poetry >/dev/null 2>&1; then
        exec poetry run python "$entry"
      else
        PY_BIN="$( [ -x ".venv/bin/python" ] && echo ".venv/bin/python" || command -v python3 || command -v python )"
        exec "$PY_BIN" "$entry"
      fi
    fi
}

# Parse commands
if [[ $# -lt 1 ]]; then
  usage
fi

cmd="$1"; shift || true
norm_cmd="$(normalize_server "$cmd")"

case "$norm_cmd" in
  status)
    [[ $# -eq 1 ]] || usage
    print_status "$1"
    ;;

  stop)
    if [[ "${1:-}" == "all" ]]; then
      echo "Stopping all MCP servers..."
      for server in "${SERVERS[@]:-}"; do
        stop_server "$server"
      done
    else
      [[ $# -eq 1 ]] || usage
      stop_server "$1"
    fi
    ;;

  all)
    # Start all discovered servers as daemons (no-op if already running)
    for server in "${SERVERS[@]:-}"; do
      launch_server "$server" "daemon"
    done
    echo "All discovered MCP servers launched (daemon mode). Use '$0 status <server>' to check or '$0 stop <server>' to stop."
    ;;

  compute|db|network|security|observability|cost|inventory|blockstorage|loadbalancer|loganalytics|unified|agents|objectstorage)
    mode="foreground"
    # Parse optional flags: --daemon, --http, --sse, --stream|--streamable|--streamable-http, --host <host>, --port <port>
    while [[ $# -gt 0 ]]; do
      case "${1:-}" in
        --daemon) mode="daemon"; shift ;;
        --http) export MCP_TRANSPORT="http"; shift ;;
        --sse) export MCP_TRANSPORT="sse"; shift ;;
        --stream|--streamable|--streamable-http) export MCP_TRANSPORT="streamable-http"; shift ;;
        --host) export MCP_HOST="${2:-127.0.0.1}"; shift 2 ;;
        --port) export MCP_PORT="${2:-8000}"; shift 2 ;;
        *) break ;;
      esac
    done
    launch_server "$norm_cmd" "$mode"
    ;;

  *)
    usage
    ;;
esac

# If we launched anything in foreground, that exec'd and did not return.
# For daemon or management commands, just exit cleanly.
exit 0
