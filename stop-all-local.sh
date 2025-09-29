#!/usr/bin/env bash
# Stop all MCP-OCI components: MCP servers, UX app, and observability stack

set -euo pipefail

log()  { printf "\033[1;34m[INFO]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }

usage() {
  cat <<EOF
Usage: $0 [--keep-observability]

Options:
  --keep-observability   Keep the observability stack running (only stop MCP servers and UX)
EOF
}

KEEP_OBSERVABILITY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep-observability) KEEP_OBSERVABILITY=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) warn "Unknown option: $1"; usage; exit 1 ;;
  esac
done

log "Stopping MCP-OCI components..."

# Stop all MCP servers
log "Stopping all MCP servers..."
scripts/mcp-launchers/start-mcp-server.sh stop all || warn "Some MCP servers may not have been running"

# Stop UX application
log "Stopping UX application..."
pkill -f "uvicorn ux.app:app" || warn "UX app may not have been running"

# Stop observability stack unless requested to keep it
if [[ "$KEEP_OBSERVABILITY" != "true" ]]; then
  log "Stopping observability stack..."
  cd ops
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose down || warn "Docker compose down failed"
  elif docker compose version >/dev/null 2>&1; then
    docker compose down || warn "Docker compose down failed"
  else
    warn "Docker Compose not found, cannot stop observability stack"
  fi
  cd ..
else
  log "Keeping observability stack running as requested"
fi

log "All components stopped!"
echo ""
echo "To restart everything:"
echo "  ./run-all-local.sh"
echo ""
echo "To start only MCP servers:"
echo "  scripts/mcp-launchers/start-mcp-server.sh all --daemon"
echo ""
echo "To start only UX app:"
echo "  cd ops && ./run-ux-local.sh"