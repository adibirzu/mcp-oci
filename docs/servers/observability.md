Observability MCP Server (oci-mcp-observability) - SDK/REST Reference and Correlation Guide

Overview
- Purpose: One-stop interface for OCI Logging Analytics (Logan), Monitoring-to-Logs correlation, diagnostics, and OTEL-enhanced observability. Wraps the consolidated Log Analytics implementation while adding high-level utilities.
- FASTMCP readiness:
  - OTEL tracing on all tools; optional Prometheus /metrics.
  - Doctor/doctor_all tools to verify server health across the MCP suite.
- Primitives:
  - Logan query rows normalized to list of dicts (column-name -> value).
  - Time range inputs like 60m, 24h, 7d.

Key OCI Python SDK/REST Links
- SDK index: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/pythonsdk.htm
- MonitoringClient.summarize_metrics_data:
  https://docs.oracle.com/en-us/iaas/tools/python/latest/api/monitoring/client/oci.monitoring.MonitoringClient.html#oci.monitoring.MonitoringClient.summarize_metrics_data
- LogAnalyticsClient (list_namespaces, query, get_query_result):
  https://docs.oracle.com/en-us/iaas/tools/python/latest/api/log_analytics/client/oci.log_analytics.LogAnalyticsClient.html
- Log Analytics REST (Search Query): POST /20200601/namespaces/{namespaceName}/search/actions/query
  https://docs.oracle.com/en-us/iaas/api/#/en/loganalytics/20200601/Search/SearchQuery

Namespace Discovery
- SDK: LogAnalyticsClient.list_namespaces (preferred)
- Fallback: ObjectStorageClient.get_namespace (only if LA namespace discovery is unavailable)

Core Tools and API Mappings

1) run_log_analytics_query
- What it does: Execute an LA query using SDK QueryDetails (sync or async via work request).
- SDK calls:
  - LogAnalyticsClient.query (with QueryDetails, sub_system="LOG")
  - For async work requests: LogAnalyticsClient.get_query_result
- Notes: Supports limit, relative time_range (via TimeRange), and pagination via opc-next-page where needed.

2) run_saved_search
- What it does: Execute a saved search via QueryDetails(saved_search_id=...).
- SDK calls:
  - LogAnalyticsClient.query with saved_search_id
  - Manual pagination handling via opc-next-page
- Output: Aggregated list of shaped rows across all pages.

3) execute_logan_query (wrapper of consolidated LA server execute_query)
- What it does: Validates/enhances query locally, then calls LA via signed REST; supports 201 async flow (polled by SDK).
- REST:
  - POST /search/actions/query with Signer
- SDK:
  - LogAnalyticsClient.get_query_result (when async 201 is returned)
- Notes: Adds compartmentIdInSubtree, time filter, and query_name metadata.

4) search_security_events, get_mitre_techniques, analyze_ip_activity
- What they do: Prebuilt security queries and MITRE ATT&CK mapping; run via execute_logan_query.
- REST/SDK: Same as execute_logan_query.

5) execute_statistical_analysis
- What it does: stats/timestats/eventstats/top/bottom/frequent/rare with flexible aggregations/group-by.
- REST/SDK: Same as execute_logan_query.

6) execute_advanced_analytics
- What it does: cluster, link, nlp, classify, outlier, sequence, geostats, timecluster.
- REST/SDK: Same as execute_logan_query.

7) validate_query, get_documentation
- Local helpers for Logan syntax validation/enhancement and builtin docs.

8) check_oci_connection, quick_checks
- What they do:
  - check_oci_connection: verifies namespace resolution and runs a small head query
  - quick_checks: head, fields, and multiple stats-by-source variants
- SDK/REST: Namespace via SDK; small REST query via execute_logan_query for data check.

9) correlate_metrics_with_logs (NEW)
- What it does: Correlate Monitoring spikes (e.g., CPU) for a compute instance with Logan results; optionally restrict to VCN Flow Logs.
- SDK calls:
  - MonitoringClient.summarize_metrics_data (namespace: oci_computeagent; metric: CpuUtilization by default)
- REST/SDK for logs:
  - Logan query via execute_logan_query (REST with Signer + optional SDK polling if 201)
- Algorithm:
  - Detect contiguous spike windows where metric >= threshold
  - For each window, run Logan query constrained by:
    - resourceId = "<instance_ocid>"
    - Time > date('<window_start_iso>') and Time < date('<window_end_iso>')
    - Optional "'Log Source' = 'VCN Flow Logs'"
  - Summarize by 'Log Source'

Signed REST Usage (for Logan)
- Signer: oci.signer.Signer(tenancy, user, fingerprint, key_file, pass_phrase)
- requests.post(url, json=payload, auth=signer)
- Reference: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/pythonsdk.htm

Correlation Recipes

A) CPU spikes -> Logs (by resourceId)
- Step 1: Use correlate_metrics_with_logs with instance_id=<ocid>, metric="CpuUtilization", threshold=80, time_range="24h"
- Step 2: Inspect spike_windows[].log_summary to see log sources active within each spike window
- Optional: include_flow_logs=true to focus on VCN Flow Logs only

B) Flow Logs hotspot analysis
- Run quick_checks then execute_logan_query with:
  "* | where Time > dateRelative(1h) and 'Log Source' = 'VCN Flow Logs' | stats COUNT as hits by 'Destination Port' | sort -hits | head 20"
- Combine with instance private IPs from Compute MCP to filter Flow Logs to specific assets.

Connectivity & Permissions
- Logan: tenancy authorized for Log Analytics and the compartment(s) you search
- Monitoring: read access on metrics in the compartment(s)
- Region: set OCI_REGION or pass region param consistently across calls

Diagnostics
- diagnostics_loganalytics_stats: runs multiple 'stats by Log Source' variants and reports which one worked (count>0)
- doctor_all: aggregates doctor/healthcheck across all MCP servers for a one-shot readiness report

Maintenance Checklist
- Keep Monitoring and Logan API usage aligned with latest SDK/REST docs
- Confirm namespace resolution logic when new namespaces are onboarded
- Validate log source naming conventions (e.g., 'VCN Flow Logs') in your tenancy; adjust queries if the source label changes
