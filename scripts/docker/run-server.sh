#!/usr/bin/env bash
#
# Run a specific MCP-OCI server inside the project Docker image.
# Usage:
#   scripts/docker/run-server.sh <server> [--] [python-args...]
# Examples:
#   scripts/docker/run-server.sh compute
#   scripts/docker/run-server.sh network -- --port 8016 --transport http
#
# The script will ensure the image exists, mounting the current workspace and
# OCI configuration directory so that the container can authenticate.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

IMAGE_NAME="${IMAGE_NAME:-mcp-oci}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_REF="${IMAGE_NAME}:${IMAGE_TAG}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <server> [--] [python-args...]" >&2
  exit 1
fi

SERVER_RAW="$1"
shift

# Normalise server name to align with directory/module names
SERVER="${SERVER_RAW//-/_}"
SERVER="${SERVER,,}"

declare -A SERVER_MODULES=(
  ["compute"]="mcp_servers.compute.server"
  ["db"]="mcp_servers.db.server"
  ["database"]="mcp_servers.db.server"
  ["network"]="mcp_servers.network.server"
  ["networking"]="mcp_servers.network.server"
  ["security"]="mcp_servers.security.server"
  ["observability"]="mcp_servers.observability.server"
  ["cost"]="mcp_servers.cost.server"
  ["inventory"]="mcp_servers.inventory.server"
  ["blockstorage"]="mcp_servers.blockstorage.server"
  ["loadbalancer"]="mcp_servers.loadbalancer.server"
  ["loganalytics"]="mcp_servers.loganalytics.server"
  ["agents"]="mcp_servers.agents.server"
)

MODULE="${SERVER_MODULES[${SERVER}]:-}"
if [[ -z "${MODULE}" ]]; then
  echo "Unknown server '${SERVER_RAW}'. Available options:" >&2
  printf '  - %s\n' "${!SERVER_MODULES[@]}" | sort >&2
  exit 2
fi

if ! docker image inspect "${IMAGE_REF}" >/dev/null 2>&1; then
  echo "Docker image ${IMAGE_REF} not found; building it first..." >&2
  IMAGE_NAME="${IMAGE_NAME}" IMAGE_TAG="${IMAGE_TAG}" scripts/docker/build.sh
fi

OCI_CONFIG_DIR="${OCI_CONFIG_DIR:-${HOME}/.oci}"
if [[ ! -d "${OCI_CONFIG_DIR}" ]]; then
  echo "Warning: OCI configuration directory '${OCI_CONFIG_DIR}' not found. The container may not authenticate." >&2
fi

PYTHON_CMD=("python" "-m" "${MODULE}")
if [[ $# -gt 0 ]]; then
  if [[ "$1" == "--" ]]; then
    shift
  fi
  PYTHON_CMD+=("$@")
fi

# Collect environment variables to forward into the container without forcing defaults
FORWARD_VARS=(
  OCI_PROFILE
  OCI_REGION
  COMPARTMENT_OCID
  TENANCY_OCID
  ALLOW_MUTATIONS
  MCP_TRANSPORT
  MCP_HOST
  MCP_PORT
  MCP_OCI_PRIVACY
  OTEL_EXPORTER_OTLP_ENDPOINT
  OTEL_EXPORTER_OTLP_PROTOCOL
  ENABLE_PYROSCOPE
  PYROSCOPE_SERVER_ADDRESS
  PYROSCOPE_APP_NAME
  LA_NAMESPACE
  FINOPSAI_CACHE_TTL_SECONDS
)

DOCKER_ENV_ARGS=()
for var in "${FORWARD_VARS[@]}"; do
  if [[ -n "${!var:-}" ]]; then
    DOCKER_ENV_ARGS+=("-e" "${var}=${!var}")
  fi
done

DOCKER_ENV_ARGS+=(
  -e "PYTHONPATH=/workspace/src:/workspace"
  -e "MCP_TRANSPORT=${MCP_TRANSPORT:-stdio}"
  -e "OTEL_EXPORTER_OTLP_ENDPOINT=${OTEL_EXPORTER_OTLP_ENDPOINT:-localhost:4317}"
  -e "MCP_OCI_PRIVACY=${MCP_OCI_PRIVACY:-true}"
)

DOCKER_RUN_ARGS=(
  --rm
  -i
  -v "${ROOT_DIR}:/workspace"
  -w /workspace
)

if [[ -d "${OCI_CONFIG_DIR}" ]]; then
  DOCKER_RUN_ARGS+=(-v "${OCI_CONFIG_DIR}:/root/.oci:ro")
fi

echo "Starting MCP server '${SERVER}' in Docker image ${IMAGE_REF}..." >&2
docker run \
  "${DOCKER_RUN_ARGS[@]}" \
  "${DOCKER_ENV_ARGS[@]}" \
  "${IMAGE_REF}" \
  bash -lc "$(printf '%q ' "${PYTHON_CMD[@]}")"
