# OCI Inventory MCP Server (`oci-mcp-inventory`)

## Overview
- Purpose: Cross-service resource discovery, tag search, cost hints.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8009` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| `doctor` | Return server health, config summary, and masking status |
| `generate_compute_capacity_report` | Generate comprehensive compute capacity report with utilization analysis and recommendations |
| `healthcheck` | Lightweight readiness/liveness check for the inventory server |
| `list_all_discovery` | Aggregate discovery of core resources in a compartment |
| `list_functions_applications_inventory` | List OCI Functions applications (discovery shortcut for inventory) |
| `list_load_balancers_inventory` | List OCI Load Balancers (discovery shortcut for inventory) |
| `list_security_lists_inventory` | List OCI Networking security lists (discovery shortcut for inventory) |
| `list_streams_inventory` | List OCI Streaming streams (discovery shortcut for inventory) |
| `run_showoci` | Run ShowOCI inventory report with optional diff for changes |
| `run_showoci_simple` | Run ShowOCI using comma-separated regions/compartments/resource_types |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh inventory`
- CLI entrypoint: `mcp-oci-serve inventory`
- Docker helper: `scripts/docker/run-server.sh inventory`
- Stop daemonised instance: `scripts/mcp-launchers/start-mcp-server.sh stop inventory`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Service-specific hints:
  - `COMPARTMENT_OCID`
  - `INVENTORY_INCLUDE_TAGS`

## Testing notes
- Unit: see `tests/unit/test_mcp_servers.py` (faked OCI responses).
- Manual: `python -m mcp_servers.inventory.server` launches the FastMCP runtime.

