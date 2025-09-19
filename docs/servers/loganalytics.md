# OCI Log Analytics Server

Exposes `oci:loganalytics:*` tools (logan-api-spec 20200601). Namespace is auto-discovered for the tenancy; you don’t need to pass it.

## Tools
- `oci:loganalytics:execute_query` — Run a Log Analytics query for a time range.
- `oci:loganalytics:search_security_events` — Natural-language search for security events.
- `oci:loganalytics:get_mitre_techniques` — Search for MITRE ATT&CK techniques.
- `oci:loganalytics:analyze_ip_activity` — Analyze activity for an IP.
- `oci:loganalytics:perform_statistical_analysis` — Run stats/timestats/eventstats.
- `oci:loganalytics:perform_advanced_analytics` — Run specialized analytics.
- `oci:loganalytics:list_sources` — List sources in a compartment.
- `oci:loganalytics:list_entities` — List entities in a compartment.
- `oci:loganalytics:get_log_sources_last_days` — Recent active sources.

## Usage
Serve (recommended): use the consolidated Observability server which includes Log Analytics tools.
```
"mcpServers": {
  "oci-mcp-observability": {
    "command": "python",
    "args": ["mcp_servers/observability/server.py"]
  }
}
```

Tool call example:
```
tools/call name=oci:loganalytics:execute_query arguments={
  "query": "* | head 5",
  "time_range": "1h",
  "compartment_id": "ocid1.compartment.oc1..xxxxx"
}
```

## Parameters
- execute_query: `query` (required), `compartment_id` (required), `time_range` (default `24h`), `max_count?`.
- list_sources: `compartment_id` (required), `limit?`.
- list_entities: `compartment_id` (required), `limit?`.
- Others list their fields in tools/list; namespace is auto-discovered.

## Troubleshooting
- Ensure your user/profile has permissions for Log Analytics.
- For query errors about payload shape: server now uses `QueryDetails` (SDK) or matching REST schema `{ subSystem, queryString, timeFilter: {timeStart, timeEnd}, maxTotalCount }`.
- Connection stability: stdio server tolerates empty/malformed frames and keeps the session alive; use `mcp:server:ping` to verify.
- If you use the aggregated FastMCP server, Log Analytics tools are disabled by default to avoid duplication. Set `MCP_OCI_ENABLE_FASTMCP_LOGAN=1` to enable them explicitly.

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
