#!/usr/bin/env bash
set -euo pipefail

# Full AIOps deploy: venv, install, provision AJD (optional), create tables, populate data,
# start Observability MCP server and Web3 AIOps agent.

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR/src:$ROOT_DIR"

# --- Bootstrap .env and OCI CLI/config if missing ---
if [ ! -f .env ]; then
  echo "No .env found. Create one now? [Y/n]"
  read -r ans
  ans=${ans:-Y}
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    if [ -f .env.sample ]; then
      echo "Creating .env from .env.sample..."
      cp .env.sample .env
      echo ".env created. Please review and edit values if needed."
    else
      echo "Creating .env with guided prompts..."
      default_profile=${OCI_PROFILE:-DEFAULT}
      default_region=${OCI_REGION:-eu-frankfurt-1}
      default_comp=${COMPARTMENT_OCID:-ocid1.compartment.oc1..your-compartment-ocid}
      printf "OCI_PROFILE [%s]: " "$default_profile"; read -r v1; v1=${v1:-$default_profile}
      printf "OCI_REGION [%s]: " "$default_region"; read -r v2; v2=${v2:-$default_region}
      printf "COMPARTMENT_OCID [%s]: " "$default_comp"; read -r v3; v3=${v3:-$default_comp}
      printf "ALLOW_MUTATIONS [false]: "; read -r v4; v4=${v4:-false}
      cat > .env <<EOF
OCI_PROFILE=$v1
OCI_REGION=$v2
COMPARTMENT_OCID=$v3
ALLOW_MUTATIONS=$v4

# Optional caching
MCP_CACHE_TTL=3600
MCP_CACHE_TTL_COMPUTE=3600
MCP_CACHE_TTL_NETWORKING=1800
MCP_CACHE_TTL_FUNCTIONS=1800
MCP_CACHE_TTL_STREAMING=1200

# Optional: Web3 UX + Autonomous DB (wallet mode)
# ORACLE_DB_USER=ADMIN
# ORACLE_DB_PASSWORD=ChangeMe123!
# ORACLE_DB_SERVICE=abcdefg_aiops_high
# ORACLE_DB_WALLET_ZIP=/absolute/path/to/Wallet_AIOps.zip
# ORACLE_DB_WALLET_PASSWORD=ChangeMe123!

# Optional: Provision AJD on first deploy
# ADMIN_PASSWORD=ChangeMe123!
# DISPLAY_NAME=aiops-ajd
# DB_NAME=AIOPSAJD

# Optional: OCI Generative AI Agents chat proxy for Web3 UX
# GAI_AGENT_ENDPOINT=http://localhost:8088/agents/chat
# GAI_AGENT_API_KEY=your-api-key
EOF
      echo ".env written."
    fi
  else
    echo "Skipping .env creation. You can copy from .env.example."
  fi
fi

# Load .env if present
if [ -f .env ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs -0 -I{} echo {} | tr '\n' ' ' | sed 's/ *$//') || true
fi

# Ensure OCI CLI is installed and configured
if ! command -v oci >/dev/null 2>&1; then
  echo "OCI CLI not found. Install now? [Y/n]"
  read -r ans
  ans=${ans:-Y}
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    if command -v brew >/dev/null 2>&1; then
      echo "> Installing oci-cli via Homebrew"
      brew install oci-cli || true
    else
      echo "> Installing oci-cli via official installer (requires curl and interactive prompts)"
      bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)" || true
      # Add CLI to PATH for current session if installed in default location
      if [ -f "$HOME/bin/oci" ]; then export PATH="$HOME/bin:$PATH"; fi
      if [ -f "$HOME/.local/bin/oci" ]; then export PATH="$HOME/.local/bin:$PATH"; fi
    fi
  else
    echo "Skipping OCI CLI installation."
  fi
fi

# Ensure OCI config exists
if [ ! -f "${OCI_CONFIG_FILE:-$HOME/.oci/config}" ]; then
  echo "No OCI config found at ${OCI_CONFIG_FILE:-$HOME/.oci/config}. Run 'oci setup config' now? [Y/n]"
  read -r ans
  ans=${ans:-Y}
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    oci setup config || true
  else
    echo "Proceeding without generating config. SDK may use instance principals if available."
  fi
fi

choose_python(){ if command -v python3 >/dev/null 2>&1; then echo python3; else echo python; fi; }
PY=$(choose_python)

if [ ! -d .venv ]; then "$PY" -m venv .venv; fi
. .venv/bin/activate
pip install -U pip
set +e
pip install -e .[dev]
if [ $? -ne 0 ]; then
  echo "> Editable install failed; falling back to requirements.txt"
  if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
fi
set -e
pip install fastapi uvicorn oracledb || true

echo "> Testing DB connectivity (wallet or DSN envs required)"
if ! .venv/bin/python scripts/test_db_connection.py; then
  echo "DB not reachable. Attempting to provision AJD (if COMPARTMENT_OCID and ADMIN_PASSWORD are set)."
  if [ -n "${COMPARTMENT_OCID:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
    DISPLAY_NAME=${DISPLAY_NAME:-aiops-ajd}
    DB_NAME=${DB_NAME:-AIOPSAJD}
    echo "> Provisioning AJD ${DISPLAY_NAME}..."
    .venv/bin/python scripts/provision_ajd.py --compartment "$COMPARTMENT_OCID" --display-name "$DISPLAY_NAME" --db-name "$DB_NAME" --admin-password "$ADMIN_PASSWORD" || true
    if [ -n "${ORACLE_DB_WALLET_ZIP:-}" ] && [ -n "${ORACLE_DB_WALLET_PASSWORD:-}" ]; then
      echo "> Generating wallet to ${ORACLE_DB_WALLET_ZIP} ..."
      WALLET_PASSWORD="$ORACLE_DB_WALLET_PASSWORD" OUTPUT_ZIP="$ORACLE_DB_WALLET_ZIP" DISPLAY_NAME="$DISPLAY_NAME" .venv/bin/python scripts/generate_wallet.py --compartment "$COMPARTMENT_OCID" || true
    fi
    echo "> Re-testing DB connectivity after provisioning"
    .venv/bin/python scripts/test_db_connection.py || (echo "ERROR: DB still unreachable. Set wallet envs and retry."; exit 1)
  else
    echo "WARN: Missing COMPARTMENT_OCID/ADMIN_PASSWORD for AJD provisioning. Skipping."
  fi
fi

echo "> Creating tables"
.venv/bin/python scripts/create_tables.py || true
echo "> Populating tables"
.venv/bin/python scripts/populate_db_from_mcp.py || true

mkdir -p logs

echo "> Warming MCP caches/registry"
PYTHONPATH="$PYTHONPATH" .venv/bin/python scripts/warm_after_deploy.py || true

stop_if_running(){
  local pidfile="$1"; local name="$2"
  if [ -f "$pidfile" ]; then
    local pid
    pid=$(cat "$pidfile" 2>/dev/null || true)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "> Stopping previous $name (pid=$pid)"
      kill "$pid" 2>/dev/null || true
      sleep 1
    fi
    rm -f "$pidfile" || true
  fi
}

stop_if_running logs/observability.pid "observability"
stop_if_running logs/web3_ux.pid "web3_ux"

echo "> Starting Observability MCP server (background)"
nohup .venv/bin/python mcp_servers/observability/server.py > logs/observability.log 2>&1 &
echo $! > logs/observability.pid

WEB3_UX_PORT=${WEB3_UX_PORT:-8080}
export WEB3_UX_PORT
echo "> Starting Web3 AIOps agent on :${WEB3_UX_PORT} (background)"
nohup .venv/bin/python web3_ux/server.py > logs/web3_ux.log 2>&1 &
echo $! > logs/web3_ux.pid

echo "Deployment complete. Logs in logs/."
