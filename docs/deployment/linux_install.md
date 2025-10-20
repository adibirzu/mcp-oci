Linux Installation Guide

Prerequisites
- Linux host (Ubuntu/RHEL/Alma/etc.)
- Python 3.11+ and Git installed
- OCI credentials: either ~/.oci/config (DEFAULT profile) or Instance Principal

Install steps
```bash
# 1) Clone
git clone https://github.com/adibirzu/mcp-oci.git
cd mcp-oci

# 2) Python venv + install
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[oci]

# 3) Set defaults (optional)
export OCI_PROFILE=DEFAULT
export OCI_REGION=eu-frankfurt-1

# 4) Start all servers (daemon)
scripts/mcp-launchers/start-mcp-server.sh all --daemon

# 5) Verify
python scripts/smoke_check.py
```

Operations
- Stop: `scripts/mcp-launchers/start-mcp-server.sh stop all`
- Status: `scripts/mcp-launchers/start-mcp-server.sh status <server>`
- Toggle privacy: `export MCP_OCI_PRIVACY=true|false` (true recommended)

Notes
- The launcher sets OpenTelemetry defaults; point OTLP endpoint via `OTEL_EXPORTER_OTLP_ENDPOINT`.
- The Log Analytics namespace is auto-discovered; if multiple exist, set `LA_NAMESPACE`.
