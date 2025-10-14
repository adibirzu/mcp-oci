# Cline (VS Code) Integration

Cline can launch MCP servers via the cline.mcpServers setting in VS Code’s settings.json. The examples below mirror this repository’s mcp.json so your local behavior is consistent.

Edit settings.json
- Command Palette → “Preferences: Open Settings (JSON)”
- Add/merge the following block (adjust paths/regions as needed)

Recommended mappings (aligns with mcp.json)
{
  "cline.mcpServers": {
    "oci-mcp-compute": {
      "command": "python",
      "args": ["mcp_servers/compute/server.py"]
    },
    "oci-mcp-db": {
      "command": "python",
      "args": ["mcp_servers/db/server.py"]
    },
    "oci-mcp-network": {
      "command": "python",
      "args": ["mcp_servers/network/server.py"]
    },
    "oci-mcp-security": {
      "command": "python",
      "args": ["mcp_servers/security/server.py"]
    },
    "oci-mcp-observability": {
      "command": "python",
      "args": ["mcp_servers/observability/server.py"]
    },
    "oci-mcp-cost": {
      "command": "python",
      "args": ["-m", "mcp_servers.cost.server"]
    },
    "oci-mcp-inventory": {
      "command": "python",
      "args": ["mcp_servers/inventory/server.py"]
    },
    "oci-mcp-blockstorage": {
      "command": "python",
      "args": ["mcp_servers/blockstorage/server.py"]
    },
    "oci-mcp-loadbalancer": {
      "command": "python",
      "args": ["mcp_servers/loadbalancer/server.py"]
    },
    "oci-mcp-agents": {
      "command": "python",
      "args": ["mcp_servers/agents/server.py"]
    }
  }
}

Environment configuration
- Configure OCI in your shell or system:
  - export OCI_PROFILE=DEFAULT
  - export OCI_REGION=eu-frankfurt-1
  - Optional: export COMPARTMENT_OCID=ocid1.compartment.oc1..example
  - Optional: export MCP_OCI_PRIVACY=true
  - Optional OTLP: export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
- If your VS Code environment does not inherit your shell, set these variables in your OS environment or a devcontainer.
- PYTHONPATH is not strictly required when running from the repo root; if needed:
  - export PYTHONPATH=<repo-root>/src:<repo-root>

Notes
- The commands above launch each server over stdio (Cline’s preferred transport).
- These servers also expose OTLP traces/metrics when OTEL_EXPORTER_OTLP_ENDPOINT is set.
- For HTTP metrics endpoints, set METRICS_PORT (e.g., 8001 for compute, 8003 for observability).
- To stop or manage daemonized servers started via shell scripts, use scripts/mcp-launchers/start-mcp-server.sh.

Alternative: single CLI wrapper
If you use the unified CLI wrapper mcp-oci-serve (as referenced in the README), you can configure servers like:
{
  "cline.mcpServers": {
    "oci-compute": {
      "command": "mcp-oci-serve",
      "args": ["compute", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    }
  }
}
This requires mcp-oci-serve to be on PATH (installed in your venv/system).

Docker-based option
{
  "cline.mcpServers": {
    "oci-mcp-compute": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "${env:HOME}/.oci:/root/.oci",
        "-v", "${workspaceFolder}:/work",
        "-w", "/work",
        "mcp-oci:latest",
        "python", "mcp_servers/compute/server.py"
      ]
    }
  }
}

Troubleshooting
- Run mcp-oci doctor --profile DEFAULT --region eu-frankfurt-1 in a terminal to verify OCI access.
- Use DEBUG=1 when debugging a specific server to increase log verbosity.
- If LA has multiple namespaces, set LA_NAMESPACE explicitly for oci-mcp-observability.
