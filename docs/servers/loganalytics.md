# OCI Log Analytics MCP Server (`oci-mcp-loganalytics`)

## Overview
- Purpose: Logging Analytics queries, MITRE mapping, and correlation helpers.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8003` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| _none_ | Tools load dynamically at runtime |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh loganalytics`
- CLI entrypoint: `mcp-oci-serve loganalytics`
- Docker helper: `scripts/docker/run-server.sh loganalytics`
- Stop daemonised instance: `scripts/mcp-launchers/start-mcp-server.sh stop loganalytics`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Service-specific hints:
  - `LA_NAMESPACE`
  - `COMPARTMENT_OCID`
  - `LA_HTTP_RETRIES`

## Testing notes
- Unit: see `tests/unit/test_mcp_servers.py` (faked OCI responses).
- Manual: `python -m mcp_servers.loganalytics.server` launches the FastMCP runtime.

