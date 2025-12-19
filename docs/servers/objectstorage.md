# OCI Object Storage MCP Server (`oci-mcp-objectstorage`)

## Overview
- Purpose: Buckets/objects inventory, usage reporting, and pre-authenticated requests.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8012` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| `healthcheck` | Lightweight readiness/liveness check for the object storage server |
| `doctor` | Return server health, config summary, and masking status |
| `list_buckets` | List buckets in the compartment/namespace |
| `get_bucket` | Get bucket details |
| `list_objects` | List objects in a bucket (prefix filtering supported) |
| `get_bucket_usage` | Get bucket usage summary (bytes, object count) |
| `get_storage_report` | Storage report across buckets (top-N, totals) |
| `list_db_backups` | List database backup artifacts stored in Object Storage |
| `get_backup_details` | Get details for a specific backup artifact |
| `create_preauthenticated_request` | Create a pre-authenticated request (PAR) for a bucket/object |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh objectstorage`
- Docker helper: `scripts/docker/run-server.sh objectstorage`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Common env vars:
  - `COMPARTMENT_OCID`
  - `ALLOW_MUTATIONS`
  - `MCP_CACHE_TTL`

