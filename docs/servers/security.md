# OCI Security MCP Server (`oci-mcp-security`)

## Overview
- Purpose: IAM inventory, Cloud Guard problems, Data Safe findings.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8004` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| `doctor` | Return server health, config summary, and masking status |
| `healthcheck` | Lightweight readiness/liveness check for the security server |
| `list_cloud_guard_problems` | List Cloud Guard problems |
| `list_compartments` | List all compartments in the tenancy |
| `list_data_safe_findings` | List Data Safe findings (if enabled) |
| `list_groups` | List IAM groups (read-only) |
| `list_iam_users` | List IAM users (read-only) |
| `list_policies` | List IAM policies (read-only) |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh security`
- CLI entrypoint: `mcp-oci-serve security`
- Docker helper: `scripts/docker/run-server.sh security`
- Stop daemonised instance: `scripts/mcp-launchers/start-mcp-server.sh stop security`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Service-specific hints:
  - `COMPARTMENT_OCID`
  - `SECURITY_SCAN_ENABLED`

## Testing notes
- Unit: see `tests/unit/test_mcp_servers.py` (faked OCI responses).
- Manual: `python -m mcp_servers.security.server` launches the FastMCP runtime.

