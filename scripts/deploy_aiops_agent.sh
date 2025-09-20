#!/usr/bin/env bash
set -euo pipefail

# Deploy the Web3 AIOps agent (serves web3_ux) on this host.

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
pip install -U pip
pip install fastapi uvicorn

echo "> Starting OCI MCP Web3 UX on :8080"
exec .venv/bin/python web3_ux/server.py

