# OCI Cost / FinOpsAI MCP Server (`oci-mcp-cost`)

## Overview
- Purpose: FinOps workloads with Usage API analytics, FinOpsAI focus days, budgets.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8005` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| _none_ | Tools load dynamically at runtime |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh cost`
- CLI entrypoint: `mcp-oci-serve cost`
- Docker helper: `scripts/docker/run-server.sh cost`
- Stop daemonised instance: `scripts/mcp-launchers/start-mcp-server.sh stop cost`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Service-specific hints:
  - `TENANCY_OCID`
  - `FINOPSAI_CACHE_TTL_SECONDS`
  - `FINOPSAI_CURRENCY`

## Testing notes
- Unit: see `tests/unit/test_mcp_servers.py` (faked OCI responses).
- Manual: `python -m mcp_servers.cost.server` launches the FastMCP runtime.

