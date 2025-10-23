# OCI Compute MCP Server (`oci-mcp-compute`)

## Overview
- Purpose: Instance lifecycle operations, IP discovery, metrics summaries.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8001` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| `create_instance` | Create a new compute instance |
| `doctor` | Return server health, config summary, and masking status |
| `get_instance_details_with_ips` | Get detailed instance information including all IP addresses (primary and secondary, public and private) - optimized for ShowOCI |
| `get_instance_metrics` | Get CPU metrics summary and instance details for an instance |
| `healthcheck` | Lightweight readiness/liveness check for the compute server |
| `list_instances` | List compute instances |
| `restart_instance` | Restart a compute instance (soft by default, or hard reset if specified) |
| `start_instance` | Start a compute instance |
| `stop_instance` | Stop a compute instance |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh compute`
- CLI entrypoint: `mcp-oci-serve compute`
- Docker helper: `scripts/docker/run-server.sh compute`
- Stop daemonised instance: `scripts/mcp-launchers/start-mcp-server.sh stop compute`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Service-specific hints:
  - `ALLOW_MUTATIONS`
  - `COMPARTMENT_OCID`
  - `MCP_CACHE_TTL_COMPUTE`

## Testing notes
- Unit: see `tests/unit/test_mcp_servers.py` (faked OCI responses).
- Manual: `python -m mcp_servers.compute.server` launches the FastMCP runtime.

