# OCI Load Balancer MCP Server (`oci-mcp-loadbalancer`)

## Overview
- Purpose: Load balancer inventory, backend health, certificate helpers.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8008` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| `create_load_balancer` | Create a new load balancer |
| `doctor` | Return server health, config summary, and masking status |
| `healthcheck` | Lightweight readiness/liveness check for the load balancer server |
| `list_load_balancers` | List load balancers in a compartment |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh loadbalancer`
- CLI entrypoint: `mcp-oci-serve loadbalancer`
- Docker helper: `scripts/docker/run-server.sh loadbalancer`
- Stop daemonised instance: `scripts/mcp-launchers/start-mcp-server.sh stop loadbalancer`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Service-specific hints:
  - `ALLOW_MUTATIONS`
  - `COMPARTMENT_OCID`
  - `LB_HEALTH_WINDOW`

## Testing notes
- Unit: see `tests/unit/test_mcp_servers.py` (faked OCI responses).
- Manual: `python -m mcp_servers.loadbalancer.server` launches the FastMCP runtime.

