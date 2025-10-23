# OCI Database MCP Server (`oci-mcp-db`)

## Overview
- Purpose: Autonomous Database and DB system inventory plus lifecycle actions.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8002` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| `doctor` | Return server health, config summary, and masking status |
| `get_autonomous_database` | Get detailed information about an Autonomous Database |
| `get_cost_summary_by_cloud` | Get aggregated cost summary by cloud provider |
| `get_db_cpu_snapshot` | Get CPU metrics snapshot for a database |
| `get_db_metrics` | Get performance metrics for a database resource |
| `healthcheck` | Lightweight readiness/liveness check for the database server |
| `list_autonomous_databases` | List autonomous databases |
| `list_db_systems` | List DB systems |
| `query_multicloud_costs` | Query multi-cloud cost data from Autonomous Database (AWS, Azure, OCI) |
| `restart_autonomous_database` | Restart an autonomous database |
| `restart_db_system` | Restart a DB system |
| `start_autonomous_database` | Start an autonomous database |
| `start_db_system` | Start a DB system |
| `stop_autonomous_database` | Stop an autonomous database |
| `stop_db_system` | Stop a DB system |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh db`
- CLI entrypoint: `mcp-oci-serve db`
- Docker helper: `scripts/docker/run-server.sh db`
- Stop daemonised instance: `scripts/mcp-launchers/start-mcp-server.sh stop db`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Service-specific hints:
  - `ALLOW_MUTATIONS`
  - `COMPARTMENT_OCID`
  - `ADB_PASSWORD`

## Testing notes
- Unit: see `tests/unit/test_mcp_servers.py` (faked OCI responses).
- Manual: `python -m mcp_servers.db.server` launches the FastMCP runtime.

