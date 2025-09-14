# OCI Log Analytics Server

Exposes `oci:loganalytics:*` tools (logan-api-spec 20200601).

## Tools
- `oci:loganalytics:run-query` — Run a Log Analytics query for a namespace and time range.
- `oci:loganalytics:list-entities` — List entities in a namespace.
- `oci:loganalytics:list-parsers` — List parsers.
- `oci:loganalytics:list-log-groups` — List log groups (if supported).
- `oci:loganalytics:list-saved-searches` — List saved searches.
- `oci:loganalytics:list-scheduled-tasks` — List scheduled tasks.
- `oci:loganalytics:upload-lookup` — Mutating. Upload a lookup (confirm/dry_run).
- `oci:loganalytics:list-work-requests` — List work requests.
- `oci:loganalytics:get-work-request` — Get a work request by OCID.
- `oci:loganalytics:run-snippet` — Run a convenience query snippet by name.
 - `oci:loganalytics:list-snippets` — List available snippet names.

## Usage
Serve:
```
mcp-oci-serve-loganalytics --profile DEFAULT --region us-phoenix-1
```
Dev call:
```
mcp-oci call loganalytics oci:loganalytics:run-query --params '{
  "namespace_name":"mytenant",
  "query_string":"search ""error"" | stats count()",
  "time_start":"2025-01-01T00:00:00Z",
  "time_end":"2025-01-02T00:00:00Z"
}'
```

## Parameters
- run-query: `namespace_name` (required), `query_string` (required), `time_start` (required), `time_end` (required), `subsystem?`, `max_total_count?`.
- list-entities: `namespace_name` (required), `compartment_id` (required), `limit?`, `page?`.
- list-parsers: `namespace_name` (required), `limit?`, `page?`.
- list-log-groups: `namespace_name` (required), `compartment_id` (required), `limit?`, `page?`.
- list-saved-searches: `namespace_name` (required), `limit?`, `page?`.
- list-scheduled-tasks: `namespace_name` (required), `compartment_id` (required), `limit?`, `page?`.
- upload-lookup: `namespace_name` (required), `name` (required), `file_path` (required), `description?`, `type?`, `dry_run?`, `confirm?`.
- list-work-requests: `compartment_id` (required), `namespace_name` (required), `limit?`, `page?`.
- get-work-request: `work_request_id` (required).
- run-snippet: `namespace_name` (required), `snippet` (required), `params?`, `time_start` (required), `time_end` (required), `max_total_count?`.

## Troubleshooting
- Some method names vary by SDK version; if you see an error indicating an unsupported method, update the OCI SDK.
- Ensure your user/profile has permissions for Log Analytics.
 - For upload-lookup in Docker, mount the lookup file into the container and reference its path inside the container.

## Snippets
- Use `oci:loganalytics:list-snippets` to discover available names, e.g.,
  - stats_by_log_source
  - all_network_traffic
  - top10_denied_connections_by_source
  - top10_destination_ports_by_traffic
  - top10_windows_failed_logins
  - failed_ssh_logins_by_destination
  - suricata_signature, suricata_id, suricata_signature_percentage, suricata_destination_ip_percentage
  - waf_protection_rules, waf_request_protection_capabilities_check_action
  - windows_sysmon_detected_events, windows_sysmon_not_technique_t1574_002, mitre_technique_id_non_system
  - port_scan_detection, dest_ip_fanout_detection

Example:
```
mcp-oci call loganalytics oci:loganalytics:run-snippet --params '{
  "namespace_name":"mytenant",
  "snippet":"stats_by_log_source",
  "time_start":"2025-01-01T00:00:00Z",
  "time_end":"2025-01-02T00:00:00Z"
}'
```
