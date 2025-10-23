# OCI Block Storage MCP Server (`oci-mcp-blockstorage`)

## Overview
- Purpose: Block volume inventory and creation helpers.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8007` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| `create_volume` | Create a new block storage volume |
| `doctor` | Return server health, config summary, and masking status |
| `healthcheck` | Lightweight readiness/liveness check for the block storage server |
| `list_volumes` | List block storage volumes |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh blockstorage`
- CLI entrypoint: `mcp-oci-serve blockstorage`
- Docker helper: `scripts/docker/run-server.sh blockstorage`
- Stop daemonised instance: `scripts/mcp-launchers/start-mcp-server.sh stop blockstorage`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Service-specific hints:
  - `ALLOW_MUTATIONS`
  - `COMPARTMENT_OCID`

## Testing notes
- Unit: see `tests/unit/test_mcp_servers.py` (faked OCI responses).
- Manual: `python -m mcp_servers.blockstorage.server` launches the FastMCP runtime.

