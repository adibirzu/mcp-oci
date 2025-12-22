# Observability MCP Server Runbook (oci-mcp-observability)

Use this runbook for metrics/log correlation, trace checks, and Log Analytics shortcuts.

## Inputs
- Time window
- Resource OCID or name (optional)
- Logging Analytics namespace (optional)

## Steps
1. **Baseline observability status**
   - Tool: `get_observability_metrics_summary`
2. **Set or confirm Logging Analytics namespace**
   - Tools: `list_la_namespaces`, `set_la_namespace`, `get_la_namespace`
3. **Run quick Log Analytics checks**
   - Tools: `quick_checks`, `run_log_analytics_query`
4. **Correlate logs with metrics**
   - Tool: `correlate_metrics_with_logs`
5. **Threat or IP-focused analysis (if requested)**
   - Tools: `search_security_events`, `analyze_ip_activity`, `correlate_threat_intelligence`
6. **Trace validation**
   - Tools: `analyze_trace_correlation`, `send_test_trace_notification`

## Skill/Tool mapping
- Observability summary: `get_observability_metrics_summary`
- Namespace management: `list_la_namespaces`, `set_la_namespace`, `get_la_namespace`
- Log analytics helpers: `quick_checks`, `run_log_analytics_query`
- Correlation: `correlate_metrics_with_logs`, `analyze_trace_correlation`
- Threat analysis: `search_security_events`, `analyze_ip_activity`, `correlate_threat_intelligence`

## Outputs
- Metrics/log correlation summary
- Trace verification details
- Risk indicators and next actions
