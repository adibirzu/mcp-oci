# MCP-OCI Architecture (Updated)

Overview
- Production MCP servers now live under `mcp_servers/` (FastMCP). Legacy `src/mcp_oci_*` packages remain for compatibility wrappers.
- All servers conform to common patterns for auth, observability, privacy, and tool naming.

Runtime
- Transport: JSON-RPC over stdio (via FastMCP). Each server exposes a set of tools.
- Observability: OTLP traces/metrics with optional `/metrics` Prometheus exporter when started directly.
- Privacy: Optional masking enabled by `MCP_OCI_PRIVACY=true` (default via launcher/mcp.json) redacts OCIDs, namespaces, and sensitive IDs across outputs.

Structure
- `mcp_servers/<service>/server.py` — tools for each OCI service (compute, db, network, security, cost, observability, etc.)
- `mcp_oci_common/` — shared config, privacy, observability, caching, validation
- `scripts/mcp-launchers/start-mcp-server.sh` — unified start/stop/status launcher
- `scripts/smoke_check.py` — imports modules and calls a `doctor` tool to verify health

Tool conventions
- Names: `oci:<service>:<action>` where applicable; FastMCP Tool names are human-friendly in local servers
- All servers expose `doctor` for health/config and often `healthcheck` for liveness
- Mutating operations require explicit enable via `ALLOW_MUTATIONS=true`

Log Analytics improvements
- Handles 201 Accepted by polling `get_query_result`
- Parses results from `results` (preferred) or `items`
- Adds `diagnostics_loganalytics_stats` to try multiple `stats by 'Log Source'` variants; default first matches Console

Cost server hardening
- Startup logging no longer prints to STDOUT to avoid MCP parse errors
- Doctor tool reports masking status and tool names

Client configuration
- `mcp.json` provides ready-to-use server commands for MCP clients (e.g., Claude Desktop). Each entry sets `MCP_OCI_PRIVACY=true` by default.

Deployment summary
- Linux quick start:
  1. `python3 -m venv .venv && source .venv/bin/activate && pip install -e .[oci]`
  2. `scripts/mcp-launchers/start-mcp-server.sh all --daemon`
  3. `python scripts/smoke_check.py`

Testing and validation
- Use `scripts/smoke_check.py` for a fast end-to-end server readiness check
- Unit/integration tests under `tests/` for selected services
