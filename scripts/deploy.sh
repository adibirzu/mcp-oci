#!/usr/bin/env bash
set -euo pipefail

# Production deploy helper for mcp-oci
# - Creates venv, installs deps, lints, formats, runs tests
# - Emits quick usage and server startup instructions

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

choose_python() {
  if command -v python3 >/dev/null 2>&1; then echo python3; return; fi
  if command -v python >/dev/null 2>&1; then echo python; return; fi
  echo "ERROR: python is required" >&2; exit 1
}

PY_BIN=$(choose_python)
echo "> Using Python: $($PY_BIN -V)"

if [ ! -d .venv ]; then
  "$PY_BIN" -m venv .venv
fi
. .venv/bin/activate

echo "> Installing dependencies (editable)"
pip install -U pip >/dev/null
pip install -e .[dev]

echo "> Linting and formatting"
.venv/bin/ruff check --fix .
.venv/bin/black .

echo "> Running tests"
.venv/bin/pytest -q || { echo "Tests failed" >&2; exit 1; }

cat <<EOF

Deployment ready.

Quick start:
- Ensure ~/.oci/config configured. Export defaults if desired:
    export OCI_PROFILE=DEFAULT
    export OCI_REGION=eu-frankfurt-1

- Launch Observability + Log Analytics MCP server (recommended):
    python mcp_servers/observability/server.py

- Warm registry (optional, faster name lookups):
    scripts/warm_registry.py --profile "+
EOF

