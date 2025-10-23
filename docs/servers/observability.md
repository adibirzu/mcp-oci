# OCI Observability Hub MCP Server (`oci-mcp-observability`)

## Overview
- Purpose: Cross-server diagnostics, trace helpers, Logging Analytics shortcuts.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8003` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| `analyze_ip_activity` | Analyze activity for an IP across authentication/network/threat intel |
| `analyze_trace_correlation` | Analyze trace correlation and observability data for a trace token |
| `build_advanced_query` | Build advanced Log Analytics queries for common patterns (error analysis, performance, security audit, API monitoring, etc.) |
| `check_oci_connection` | Verify Logging Analytics connectivity and run optional test query |
| `correlate_metrics_with_logs` | Correlate Monitoring spikes with Log Analytics (optionally VCN Flow Logs) |
| `correlate_threat_intelligence` | Correlate threat intelligence indicators (IPs, domains, hashes, users, URLs) with log data |
| `create_traced_operation` | Create a traced MCP operation with OpenTelemetry enhancement |
| `diagnostics_loganalytics_stats` | Run multiple 'stats by Log Source' variants and report which works |
| `doctor` | Return server health, config summary, and masking status |
| `doctor_all` | Aggregate doctor/healthcheck across all MCP-OCI servers |
| `emit_test_log` | Emit synthetic test log |
| `execute_advanced_analytics` | Advanced analytics: cluster, link, nlp, classify, outlier, sequence, geostats, timecluster |
| `execute_logan_query` | Execute enhanced OCI Logging Analytics query (Logan) |
| `execute_statistical_analysis` | Run stats/timestats/eventstats/top/bottom/frequent/rare |
| `get_documentation` | Get docs for Log Analytics query syntax, fields, functions, MITRE mapping, etc. |
| `get_la_namespace` | Get the currently selected Logging Analytics namespace |
| `get_mcp_otel_capabilities` | Get MCP server OpenTelemetry capabilities and features |
| `get_mitre_techniques` | List or analyze MITRE ATT&CK techniques in logs |
| `get_observability_metrics_summary` | Get comprehensive observability metrics and server status |
| `list_la_namespaces` | List available Logging Analytics namespaces and current selection |
| `oci_observability_clear_recent_calls` | Clear the recent MCP call buffer |
| `oci_observability_get_recent_calls` | Return recent MCP call path and query metadata (last 50) |
| `quick_checks` | Basic LA checks: head, fields, stats by source |
| `run_log_analytics_query` | Run ad-hoc Log Analytics query |
| `run_saved_search` | Run saved Log Analytics search |
| `search_security_events` | Search security events using Logan patterns or natural language |
| `send_test_trace_notification` | Send test trace notification following MCP OpenTelemetry proposal |
| `set_la_namespace` | Set the Logging Analytics namespace to use for all queries |
| `validate_query` | Validate Log Analytics query; optionally auto-fix common issues |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh observability`
- CLI entrypoint: `mcp-oci-serve observability`
- Docker helper: `scripts/docker/run-server.sh observability`
- Stop daemonised instance: `scripts/mcp-launchers/start-mcp-server.sh stop observability`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Service-specific hints:
  - `OTEL_EXPORTER_OTLP_ENDPOINT`
  - `LA_NAMESPACE`

## Testing notes
- Unit: see `tests/unit/test_mcp_servers.py` (faked OCI responses).
- Manual: `python -m mcp_servers.observability.server` launches the FastMCP runtime.

