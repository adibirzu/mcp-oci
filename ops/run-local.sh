#!/usr/bin/env bash
set -euo pipefail

# Local Observability Stack launcher (no Docker required)
# Works with either:
#   - prebuilt binaries in ops/bin (prometheus, grafana-server, tempo, otelcol)
#   - or system-installed binaries on PATH (e.g., via Homebrew on macOS)
#
# Provisioning/configs are read from ops/* subfolders.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${SCRIPT_DIR}/bin"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Config paths
PROM_CFG="${SCRIPT_DIR}/prometheus/prometheus.yml"
TEMPO_CFG="${SCRIPT_DIR}/tempo/tempo.yaml"
OTEL_CFG="${SCRIPT_DIR}/otel/otel-collector.yaml"

# Defaults for service URLs and OTLP endpoints
export GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
export PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
export TEMPO_URL="${TEMPO_URL:-http://localhost:3200}"
# OTLP endpoints used by local apps (obs-app, etc.)
# NOTE: gRPC exporters expect 'host:port' without http:// prefix
export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-localhost:4317}"

# Grafana provisioning and auth defaults (mirror docker-compose env)
export GF_PATHS_PROVISIONING="${GF_PATHS_PROVISIONING:-${SCRIPT_DIR}/grafana/provisioning}"
export GF_AUTH_ANONYMOUS_ENABLED="${GF_AUTH_ANONYMOUS_ENABLED:-true}"
export GF_AUTH_ANONYMOUS_ORG_ROLE="${GF_AUTH_ANONYMOUS_ORG_ROLE:-Viewer}"
export GF_SECURITY_ADMIN_PASSWORD="${GF_SECURITY_ADMIN_PASSWORD:-admin}"
export GF_SECURITY_ALLOW_EMBEDDING="${GF_SECURITY_ALLOW_EMBEDDING:-true}"

# Helper: find binary from ops/bin or system PATH
find_bin() {
  local name="$1"
  if [[ -x "${BIN_DIR}/${name}" ]]; then
    printf '%s' "${BIN_DIR}/${name}"
    return 0
  fi
  if command -v "${name}" >/dev/null 2>&1; then
    command -v "${name}"
    return 0
  fi
  return 1
}

need_file() {
  local f="$1"; local why="$2"
  if [[ ! -f "$f" ]]; then
    echo "ERROR: Missing file: $f ($why)" >&2
    exit 1
  fi
}

need_any_bin() {
  local name="$1"
  if ! find_bin "$name" >/dev/null 2>&1; then
    echo "Missing executable: '${name}'. Attempting installation..." >&2
    if [[ "$OSTYPE" == "darwin"* ]] && command -v brew >/dev/null 2>&1; then
      case "$name" in
        grafana-server)
          brew install grafana || true
          ;;
        prometheus)
          brew install prometheus || true
          ;;
        tempo)
          brew install tempo || brew install grafana/tap/tempo || true
          ;;
        *)
          ;;
      esac
      # Re-check after install
      if ! find_bin "$name" >/dev/null 2>&1; then
        echo "ERROR: '${name}' still not available after install. Place it in ${BIN_DIR} or ensure it's on PATH." >&2
        exit 1
      fi
    else
      echo "ERROR: Missing executable: '$name' (not found in ${BIN_DIR} or on PATH)" >&2
      echo "Install via Homebrew (macOS): brew install ${name} (grafana, prometheus, tempo, opentelemetry-collector)" >&2
      echo "Or place binaries into ${BIN_DIR}." >&2
      exit 1
    fi
  fi
}

# Validate binaries and configs
need_any_bin "prometheus"
need_any_bin "grafana-server"
need_any_bin "tempo"
# The collector binary may be named 'otelcol' or 'otelcol-contrib' depending on install source.
OTEL_BIN="$(find_bin "otelcol" || true)"
if [[ -z "${OTEL_BIN}" ]]; then
  OTEL_BIN="$(find_bin "otelcol-contrib" || true)"
fi
if [[ -z "${OTEL_BIN}" ]]; then
  echo "ERROR: Missing executable: 'otelcol' or 'otelcol-contrib' (not found in ${BIN_DIR} or on PATH)" >&2
  echo "Install via Homebrew (macOS): brew install opentelemetry-collector" >&2
  echo "Or place otelcol/otelcol-contrib into ${BIN_DIR}." >&2
  exit 1
fi
need_file "${PROM_CFG}" "Prometheus config"
need_file "${TEMPO_CFG}" "Tempo config"
need_file "${OTEL_CFG}" "OTEL Collector config"

PROM_BIN="$(find_bin prometheus)"
GRAFANA_BIN="$(find_bin grafana-server)"
TEMPO_BIN="$(find_bin tempo)"
# Prefer Alloy if available; fallback to OTEL Collector
ALLOY_BIN="$(find_bin alloy || true)"
# OTEL_BIN is already resolved above

# Logs dir
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"

# Start Prometheus
echo "Starting Prometheus..."
"${PROM_BIN}" \
  --config.file="${PROM_CFG}" \
  --web.listen-address=":9090" \
  > "${LOG_DIR}/prometheus.log" 2>&1 &
PROM_PID=$!

# Start Tempo
echo "Starting Tempo..."
"${TEMPO_BIN}" \
  -config.file="${TEMPO_CFG}" \
  > "${LOG_DIR}/tempo.log" 2>&1 &
TEMPO_PID=$!

# Start Collector: prefer Grafana Alloy if present; otherwise use OTEL Collector
if [[ -n "${ALLOY_BIN}" ]]; then
  echo "Starting Grafana Alloy..."
  # Alloy will read our pipelines from ops/alloy/config.alloy
  "${ALLOY_BIN}" run \
    --stability=experimental \
    --disable-reporting \
    --server.http.listen-addr="127.0.0.1:12345" \
    --config.file="${SCRIPT_DIR}/alloy/config.alloy" \
    > "${LOG_DIR}/alloy.log" 2>&1 &
  COLLECTOR_PID=$!
else
  echo "Starting OTEL Collector..."
  "${OTEL_BIN}" \
    --config="${OTEL_CFG}" \
    > "${LOG_DIR}/otelcol.log" 2>&1 &
  COLLECTOR_PID=$!
fi

# Start Grafana
echo "Starting Grafana..."
# Note: --homepath should point to the Grafana installation root (where public/, conf/ live).
# When using system grafana-server, --homepath is often auto-detected, so we omit it.
"${GRAFANA_BIN}" \
  > "${LOG_DIR}/grafana.log" 2>&1 &
GRAFANA_PID=$!

# Start obs-app (serves dashboards/links UI and emits OTLP to collector)
echo "Starting obs-app..."
PYTHON_BIN="${PYTHON:-python3}"
pushd "${ROOT_DIR}/obs_app" >/dev/null
"${PYTHON_BIN}" -m uvicorn app:app --host 0.0.0.0 --port 8000 \
  > "${LOG_DIR}/obs_app.log" 2>&1 &
OBS_PID=$!
popd >/dev/null

# Cleanup on exit
cleanup() {
  echo "Stopping services..."
  # Try graceful, then force
  for pid in "${PROM_PID}" "${TEMPO_PID}" "${OTEL_PID}" "${GRAFANA_PID}" "${OBS_PID}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
  sleep 2
  for pid in "${PROM_PID}" "${TEMPO_PID}" "${OTEL_PID}" "${GRAFANA_PID}" "${OBS_PID}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill -9 "${pid}" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

# Brief wait and health hints
sleep 3
echo
echo "Services started:"
echo "- Prometheus: ${PROMETHEUS_URL}"
echo "- Grafana:    ${GRAFANA_URL} (admin/${GF_SECURITY_ADMIN_PASSWORD})"
echo "- Tempo:      ${TEMPO_URL}"
echo "- OTEL Col:   OTLP gRPC http://localhost:4317, OTLP HTTP ${OTEL_EXPORTER_OTLP_ENDPOINT}"
echo "- obs-app:    http://localhost:8000"
echo
echo "Logs directory: ${LOG_DIR}"
echo "Tip: export GRAFANA_URL, PROMETHEUS_URL, TEMPO_URL, OTEL_EXPORTER_OTLP_ENDPOINT to override defaults."

# Keep foreground
wait
