#!/usr/bin/env bash
set -euo pipefail

# Bootstrap local dev environment: create venv, install deps, and verify mcp-oci

choose_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  if command -v pyenv >/dev/null 2>&1; then
    # Try pyenv shims for a recent 3.11
    if pyenv which python3 >/dev/null 2>&1; then
      echo "$(pyenv which python3)"
      return
    fi
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi
  echo "ERROR: No python interpreter found (python3/python)" >&2
  exit 127
}

PY_BIN=$(choose_python)
echo "Using Python: ${PY_BIN}"

if [ ! -d .venv ]; then
  "${PY_BIN}" -m venv .venv
fi

. .venv/bin/activate
pip install -U pip
pip install -e .
# Install runtime/test/dev tools needed by Makefile and tests
pip install -r requirements.txt
pip install pytest pytest-mock pytest-asyncio pytest-cov requests black isort flake8 mypy ruff

echo "mcp-oci CLI: $(command -v mcp-oci || echo 'not found')"
if command -v mcp-oci >/dev/null 2>&1; then
  echo "Verifying connectivity (doctor)..."
  set +e
  mcp-oci doctor
  set -e
fi
echo "Bootstrap complete. Activate venv with: . .venv/bin/activate"
