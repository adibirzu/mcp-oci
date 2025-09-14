# mcp_oci_monitoring

## Overview
OCI Monitoring MCP server. Provides tools to list metrics, summarize metric data, and read alarms.

## Tools / Resources
- `oci:monitoring:list-metrics` — List metric definitions; filter by namespace/name/resource_group.
- `oci:monitoring:summarize-metrics` — Summarize data with query and time window.
- `oci:monitoring:list-alarms` — List alarms.
- `oci:monitoring:get-alarm` — Get an alarm by OCID.

## Usage
```
mcp-oci-serve-monitoring --profile DEFAULT --region eu-frankfurt-1
mcp-oci call monitoring oci:monitoring:list-metrics --params '{"compartment_id":"ocid1.compartment...","namespace":"oci_computeagent"}'
```

## Next
See ../../docs/servers/monitoring.md for parameters and examples.
