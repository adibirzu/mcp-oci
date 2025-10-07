# mcp_oci_usageapi

## Overview
OCI Usage API MCP server for cost and usage analytics. Provides summarized usage/cost queries with grouping.

## Installation
```
make setup
```

## Tools / Resources
- `oci_usageapi_request_summarized_usages` — Request summarized usage/cost between timestamps; supports `granularity`, `group_by`, and `compartment_name`/`compartment_id` injection into dimensions.
- `oci_usageapi_cost_by_service` — Convenience. Cost grouped by service for last N days.
- `oci_usageapi_cost_by_compartment` — Convenience. Cost grouped by compartment; accepts `compartment_name`.
- `oci_usageapi_usage_by_service` — Convenience. Usage grouped by service for last N days.
- `oci_usageapi_usage_by_compartment` — Convenience. Usage grouped by compartment; accepts `compartment_name`.
- `oci_usageapi_count_instances` — Count compute instances in a compartment (by id or name), optionally including subtree.
- `oci_usageapi_correlate_costs_and_resources` — Returns cost-by-service plus resource counts by `resourceType` using Resource Search to support correlations.

## Usage
Serve:
```
mcp-oci-serve usageapi --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call usageapi oci_usageapi_request_summarized_usages --params '{"tenant_id":"ocid1.tenancy...","time_usage_started":"2025-01-01T00:00:00Z","time_usage_ended":"2025-01-31T23:59:59Z","granularity":"DAILY","query_type":"COST","group_by":["service"]}'
```

Resolve compartment name example:
```
mcp-oci call usageapi oci_usageapi_cost_by_compartment --params '{"tenant_id":"ocid1.tenancy...","days":7, "compartment_name":"MyProject"}'
```

Count instances in a compartment by name:
```
mcp-oci call usageapi oci_usageapi_count_instances --params '{"compartment_name":"MyProject"}'
```

Correlate costs and resource counts (tenancy-wide):
```
mcp-oci call usageapi oci_usageapi_correlate_costs_and_resources --params '{"tenant_id":"ocid1.tenancy...","days":30}'
```

## Next
See ../../docs/SERVERS.md for all OCI MCP servers.
