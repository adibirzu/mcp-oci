# OCI Monitoring Server

Exposes `oci:monitoring:*` tools for listing metrics, summarizing metric data, and reading alarms.

## Tools
- `oci:monitoring:list-metrics` — List metric definitions; filter by `namespace`, `name`, `resource_group`.
- `oci:monitoring:summarize-metrics` — Summarize metric data with a query between `start_time` and `end_time`.
- `oci:monitoring:list-alarms` — List alarms in a compartment.
- `oci:monitoring:get-alarm` — Get an alarm by OCID.
 - `oci:monitoring:list-metric-namespaces` — Discover metric namespaces (derived from definitions).
 - `oci:monitoring:list-resource-groups` — Discover resource groups (derived from definitions; optional namespace).
- `oci:monitoring:list-alarm-statuses` — List alarm statuses (if supported by SDK).
- `oci:monitoring:get-alarm-history` — Get alarm history for a time range.
- `oci:monitoring:summarize-metrics-window` — Wrapper to query a recent window like `1h`/`24h` with normalized resolution.
 - `oci:monitoring:list-sdk-methods` — Introspect available SDK methods on Monitoring and Alarm clients.
 - `oci:monitoring:common-compute-queries` — Return suggested Compute metrics queries.

## Usage
Serve:
```
mcp-oci-serve-monitoring --profile DEFAULT --region eu-frankfurt-1
```
Dev calls:
```
mcp-oci call monitoring oci:monitoring:list-metrics --params '{"compartment_id":"ocid1.compartment...","namespace":"oci_computeagent"}'
mcp-oci call monitoring oci:monitoring:summarize-metrics --params '{"compartment_id":"ocid1.compartment...","namespace":"oci_computeagent","query":"CpuUtilization[1m].mean()","start_time":"2025-01-01T00:00:00Z","end_time":"2025-01-01T01:00:00Z"}'
```

## Parameters
- list-metrics: `compartment_id` (required), `namespace?`, `name?`, `resource_group?`, `compartment_id_in_subtree?`, `limit?`, `page?`.
- summarize-metrics: `compartment_id` (required), `namespace` (required), `query` (required), `start_time` (required), `end_time` (required), `resolution?`.
- list-alarms: `compartment_id` (required), `lifecycle_state?`, `limit?`, `page?`.
- get-alarm: `alarm_id` (required).
 - list-metric-namespaces: `compartment_id` (required), `compartment_id_in_subtree?`, `limit_pages?`.
 - list-resource-groups: `compartment_id` (required), `namespace?`, `compartment_id_in_subtree?`, `limit_pages?`.
 - list-alarm-statuses: `compartment_id` (required), `limit?`, `page?`.
 - get-alarm-history: `alarm_id` (required), `alarm_historytype?`, `timestamp_greater_than_or_equal_to?`, `timestamp_less_than?`.
 - summarize-metrics-window: `compartment_id` (required), `namespace` (required), `query` (required), `window` (required), `resolution?`.

## Troubleshooting
- Ensure the profile has Monitoring and Alarms read permissions.
- Query syntax follows OCI Monitoring query language (e.g., `CpuUtilization[1m].mean()`).
- Some methods may not be available in older SDK versions (e.g., `list_alarm_statuses`); update the SDK if needed.
 - `list-metric-namespaces` prefers a direct API if available in your SDK; otherwise it derives namespaces from metric definitions.
