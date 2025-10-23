# OCI Networking MCP Server (`oci-mcp-network`)

## Overview
- Purpose: VCNs, subnets, route/security lists, and mutating VCN/subnet helpers.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8006` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| `create_subnet` | Create a new subnet in a VCN |
| `create_vcn` | Create a new VCN (Virtual Cloud Network) |
| `create_vcn_with_subnets` | Create a VCN with public and private subnets, gateways, and route tables in one operation |
| `create_vcn_with_subnets_rest` | Create a VCN (plus IGW, NAT, route tables, public/private subnets) using OCI REST API with signed HTTP requests |
| `doctor` | Return server health, config summary, and masking status |
| `healthcheck` | Lightweight readiness/liveness check for the network server |
| `list_subnets` | List subnets in a VCN |
| `list_vcns` | List VCNs in a compartment |
| `summarize_public_endpoints` | Summarize public endpoints in a compartment |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh network`
- CLI entrypoint: `mcp-oci-serve network`
- Docker helper: `scripts/docker/run-server.sh network`
- Stop daemonised instance: `scripts/mcp-launchers/start-mcp-server.sh stop network`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Service-specific hints:
  - `ALLOW_MUTATIONS`
  - `NET_HTTP_POOL`
  - `NET_HTTP_RETRIES`

## Testing notes
- Unit: see `tests/unit/test_mcp_servers.py` (faked OCI responses).
- Manual: `python -m mcp_servers.network.server` launches the FastMCP runtime.

