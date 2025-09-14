# mcp_oci_usageapi

## Overview
OCI Usage API MCP server for cost and usage analytics. Provides summarized usage/cost queries with grouping.

## Installation
```
make setup
```

## Tools / Resources
- `oci:usageapi:request-summarized-usages` — Request summarized usage/cost between timestamps; supports `granularity` and `group_by`.

## Usage
Serve:
```
mcp-oci-serve-usageapi --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call usageapi oci:usageapi:request-summarized-usages --params '{"tenant_id":"ocid1.tenancy...","time_usage_started":"2025-01-01T00:00:00Z","time_usage_ended":"2025-01-31T23:59:59Z","granularity":"DAILY","query_type":"COST","group_by":["service"]}'
```

## Next
See ../../docs/SERVERS.md for all OCI MCP servers.
