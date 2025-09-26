#!/usr/bin/env bash
set -euo pipefail

# Prefer absolute paths to avoid PATH issues in GUI apps
VENV_BIN=""
if [ -d ".venv/bin" ]; then
  VENV_BIN="$(pwd)/.venv/bin/"
fi

ROOT_DIR="$(pwd)"

cmd() {
  local name="$1"; shift
  if [ -n "$VENV_BIN" ] && [ -x "${VENV_BIN}${name}" ]; then
    printf '%s' "${VENV_BIN}${name}"
  else
    printf '%s' "$name"
  fi
}

CONFIG_JSON='{
  "mcpServers": {
    "oci-iam": {
      "command": "'"$(cmd mcp-oci-serve-iam)"'",
      "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1", "--log-level", "INFO"]
    },
    "oci-compute": {
      "command": "'"$(cmd mcp-oci-serve-compute)"'",
      "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    },
    "oci-objectstorage": {
      "command": "'"$(cmd mcp-oci-serve-objectstorage)"'",
      "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    },
    "oci-usageapi": {
      "command": "'"$(cmd mcp-oci-serve-usageapi)"'",
      "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    },
    "oci-monitoring": {
      "command": "'"$(cmd mcp-oci-serve-monitoring)"'",
      "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    },
    "oci-cost": {
      "command": "'"$(cmd python)"'",
      "args": ["'"${ROOT_DIR}"'/scripts/mcp-launchers/launch-cost.py"],
      "env": {
        "OCI_PROFILE": "DEFAULT",
        "OCI_REGION": "eu-frankfurt-1",
        "COMPARTMENT_OCID": "${COMPARTMENT_OCID:-}",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
      }
    },
    "oci-blockstorage": {
      "command": "'"$(cmd python)"'",
      "args": ["-m", "mcp_servers.blockstorage.server"],
      "env": {
        "OCI_PROFILE": "DEFAULT",
        "OCI_REGION": "eu-frankfurt-1",
        "COMPARTMENT_OCID": "${COMPARTMENT_OCID:-}",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
      }
    },
    "oci-loadbalancer": {
      "command": "'"$(cmd python)"'",
      "args": ["-m", "mcp_servers.loadbalancer.server"],
      "env": {
        "OCI_PROFILE": "DEFAULT",
        "OCI_REGION": "eu-frankfurt-1",
        "COMPARTMENT_OCID": "${COMPARTMENT_OCID:-}",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
      }
    },
    "oci-observability": {
      "command": "'"$(cmd python)"'",
      "args": ["-m", "mcp_servers.observability.server"],
      "env": {
        "OCI_PROFILE": "DEFAULT",
        "OCI_REGION": "eu-frankfurt-1",
        "COMPARTMENT_OCID": "${COMPARTMENT_OCID:-}",
        "LA_NAMESPACE": "${LA_NAMESPACE:-}",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
      }
    },
    "oci-inventory": {
      "command": "'"$(cmd python)"'",
      "args": ["-m", "mcp_servers.inventory.server"],
      "env": {
        "OCI_PROFILE": "DEFAULT",
        "OCI_REGION": "eu-frankfurt-1",
        "COMPARTMENT_OCID": "${COMPARTMENT_OCID:-}",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
      }
    }
  }
}'

TARGET_MACOS="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
TARGET_LINUX="$HOME/.config/Claude/claude_desktop_config.json"
TARGET_WINDOWS="${APPDATA:-}/Claude/claude_desktop_config.json"

TARGET=""
if [ -d "$(dirname "$TARGET_MACOS")" ]; then TARGET="$TARGET_MACOS"; fi
if [ -z "$TARGET" ] && [ -d "$(dirname "$TARGET_LINUX")" ]; then TARGET="$TARGET_LINUX"; fi
if [ -z "$TARGET" ] && [ -n "${APPDATA:-}" ] && [ -d "$(dirname "$TARGET_WINDOWS")" ]; then TARGET="$TARGET_WINDOWS"; fi

if [ -z "$TARGET" ]; then
  echo "Claude Desktop config directory not found. Printing config to stdout:" >&2
  echo "$CONFIG_JSON"
  exit 0
fi

mkdir -p "$(dirname "$TARGET")"
if [ -f "$TARGET" ]; then
  cp "$TARGET" "$TARGET.bak.$(date +%s)"
fi
echo "$CONFIG_JSON" > "$TARGET"
echo "Wrote Claude Desktop MCP config to $TARGET (backup created if file existed)."
