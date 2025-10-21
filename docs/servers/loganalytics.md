OCI Log Analytics MCP Server (oci-mcp-loganalytics) - SDK/REST Reference and Correlation Guide

Overview
- Purpose: Execute OCI Log Analytics queries, provide security search, MITRE ATT&CK mapping, and advanced analytics. Includes both REST (signed) and SDK-assisted flows for reliability and performance.
- FASTMCP readiness:
  - Tracing: All tools are wrapped with tool_span (OTEL) and include OCI attributes.
  - Health: Use oci-mcp-observability doctor/health where applicable; this server exposes validation and connection checks.
- Primitives:
  - Query result rows: list of rows (field/value) normalized for downstream processing.
  - Time windows: accepts 1h, 6h, 12h, 24h, 1d, 7d, 30d, 1w, 1m.

Key OCI Python SDK/REST Links
- Python SDK landing: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/pythonsdk.htm
- Deep reference: https://deepwiki.com/oracle/oci-python-sdk/5-tools-and-utilities
- REST API index: https://docs.oracle.com/en-us/iaas/api/
- Log Analytics REST (Search Query): POST /20200601/namespaces/{namespaceName}/search/actions/query

Namespace Discovery
- SDK: oci.log_analytics.LogAnalyticsClient.list_namespaces
  - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/log_analytics/client/oci.log_analytics.LogAnalyticsClient.html#oci.log_analytics.LogAnalyticsClient.list_namespaces
- Fallback SDK: oci.object_storage.ObjectStorageClient.get_namespace
  - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/object_storage/client/oci.object_storage.ObjectStorageClient.html#oci.object_storage.ObjectStorageClient.get_namespace

Core Tools and API Mappings

1) oci_loganalytics_execute_query (execute_query)
- What it does: Executes a Log Analytics query for a compartment and time range. Enhances/validates query, runs via REST with SDK Signer. Supports synchronous and 201 async (work request) flows.
- REST:
  - POST /20200601/namespaces/{namespace}/search/actions/query
  - Docs: https://docs.oracle.com/en-us/iaas/api/#/en/loganalytics/20200601/Search/SearchQuery
- SDK usage:
  - Signer: oci.signer.Signer (signed REST)
  - Async polling (when 201 Accepted): oci.log_analytics.LogAnalyticsClient.get_query_result
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/log_analytics/client/oci.log_analytics.LogAnalyticsClient.html#oci.log_analytics.LogAnalyticsClient.get_query_result
- Notes:
  - Time range strings converted to ISO8601 start/end; includes compartmentId + compartmentIdInSubtree=true
  - Validation/Enhancements via query_enhancer before execution

2) oci_loganalytics_run_query (run_query_legacy)
- What it does: Legacy-compatible query with explicit namespace and timeStart/timeEnd (ISO8601).
- REST:
  - POST /20200601/namespaces/{namespace}/search/actions/query (same as above)
- SDK:
  - Signer + requests for HTTP POST

3) oci_loganalytics_search_security_events (search_security_events)
- What it does: Maps natural-language or typed patterns (failed_logins, privilege_escalation, suspicious_network, data_exfiltration, malware) to pre-built queries with time filters; executes through execute_query.
- REST/SDK: Same as execute_query; depends on enhanced query strings.
- MITRE techniques: Returns mapped techniques per query.

4) oci_loganalytics_get_mitre_techniques (get_mitre_techniques)
- What it does: Lists or executes queries for specific MITRE ATT&CK techniques (e.g., T1110).
- REST/SDK: Same as execute_query.

5) oci_loganalytics_analyze_ip_activity (analyze_ip_activity)
- What it does: Looks up activity for an IP across auth/network/threat-intel patterns. Uses query composition with stats/top/filters; executes via REST + Signer.
- REST/SDK: Same as execute_query.

6) oci_loganalytics_perform_statistical_analysis (perform_statistical_analysis)
- What it does: Runs stats, timestats, eventstats, top/bottom/frequent/rare. Accepts aggregations and group-by for flexible analysis.
- REST/SDK: Same as execute_query.

7) oci_loganalytics_perform_advanced_analytics (perform_advanced_analytics)
- What it does: Runs advanced commands: cluster, link, nlp, classify, outlier, sequence, geostats, timecluster.
- REST/SDK: Same as execute_query.

8) oci_loganalytics_validate_query (validate_query)
- What it does: Validates and enhances query syntax; returns suggestions/warnings/errors and optionally a fixed/enhanced query.
- SDK/REST: No backend call for validation; local analyzer.

9) oci_loganalytics_get_documentation (get_documentation)
- What it does: Returns help content for query syntax, functions, MITRE mapping, troubleshooting.
- SDK/REST: No backend call; local content.

10) oci_loganalytics_check_oci_connection (check_oci_connection)
- What it does: Discovers namespace via SDK; optionally executes a tiny head query via REST to confirm connectivity and data presence.
- SDK:
  - LogAnalyticsClient.list_namespaces
  - Optional REST execute_query with Signer
- REST: POST /search/actions/query (head 1)

Exadata-focused Utilities
- oci_loganalytics_exadata_cost_drilldown (exadata_cost_drilldown_logan)
- oci_loganalytics_analyze_exadata_costs (analyze_exadata_costs)
Both orchestrate one/multiple execute_query calls, then generate summary/optimization outputs.

Signed REST Usage (Python)
- Signer: oci.signer.Signer(tenancy, user, fingerprint, key_file, pass_phrase)
- Requests: requests.post(url, json=payload, auth=signer)
- Reference: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/pythonsdk.htm

Performance & Validation
- Query Enhancement: query_enhancer detects common syntax issues; may add time filters (Time > dateRelative(...)) and field quoting suggestions.
- Time Windows: Always supply a time range to reduce scan costs.
- Limit Rows: Use limit/maxTotalCount where appropriate.

Correlation Cookbook

A) Correlate High CPU Usage (Monitoring) with Log Analytics Entries
- Step 1: Fetch high-CPU instances via Monitoring
  - SDK: oci.monitoring.MonitoringClient.summarize_metrics_data (namespace: oci_computeagent; metric: CpuUtilization)
  - Docs: https://docs.oracle.com/en-us/iaas/tools/python/latest/api/monitoring/client/oci.monitoring.MonitoringClient.html#oci.monitoring.MonitoringClient.summarize_metrics_data
  - Query example (pseudo): CpuUtilization[1m]{resourceId="<instance_ocid>"}.mean()
- Step 2: For time windows with CPU spikes, run LA query for the same instance/time
  - Use execute_query with a filter on resourceId or instance-specific fields; e.g.:
    "* | where Time > dateRelative(1h) and 'resourceId' = '<instance_ocid>' | stats COUNT by 'Log Source', 'Event Name'"
- Optional: Automate correlation in a higher-level tool that iterates instances with high CPU and attaches LA results per window.

B) Correlate VCN Flow Logs with Compute/Network Events
- LA source: 'Log Source' = 'VCN Flow Logs'
- Query examples:
  - "* | where Time > dateRelative(1h) and 'Log Source' = 'VCN Flow Logs' | stats COUNT by 'Source IP', 'Destination IP', 'Action'"
  - "* | where Time > dateRelative(1h) and 'Log Source' = 'VCN Flow Logs' and 'Action' = 'BLOCK' | stats COUNT by 'Destination Port' | sort -COUNT"
- Combine with instance private IPs:
  - Get instance IPs (Compute SDK) then filter flow logs to those IPs.

C) Cross-service Correlation Outline
- Compute: list instances and IPs
  - SDK: oci.core.ComputeClient.list_instances / get_instance
- Network: derive subnets/VCN context (optionally via oci.core.VirtualNetworkClient)
- Monitoring: get high usage windows
- Log Analytics: execute queries constrained by (Time window + resourceId/IP)

Connectivity & Permissions
- Required permissions:
  - Log Analytics: read access to the namespace and logs
  - Monitoring: read metrics in the compartment(s)
  - Compute/Network: read to resolve resource metadata for correlation
- Region: Ensure OCI_REGION or per-call region is set consistently across services.

Troubleshooting
- No data returned:
  - Verify time range, compartment scope (compartmentIdInSubtree=true), and that logs are ingested.
- Authentication errors:
  - Validate config (tenancy, user, fingerprint, key file) and policy permissions.
- Query syntax:
  - Use oci_loganalytics_validate_query to auto-suggest fixes, quoting fields with spaces and adding time filters.

Examples

1) Quick sources count last 24h:
- Query: "* | where Time > dateRelative(24h) | stats COUNT as logrecords by 'Log Source' | sort -logrecords | head 100"
- Tool: oci_loganalytics_execute_query
- Params: {"query": "<above>", "compartment_id": "<ocid>", "time_range": "24h"}

2) Top failed logins 24h:
- Query: "* | where Time > dateRelative(24h) and 'Event Name' = 'UserLoginFailed' | stats COUNT as failures by 'User Name' | sort -failures | head 20"
- Tool: oci_loganalytics_execute_query

3) Flow logs blocked ports last hour:
- Query: "* | where Time > dateRelative(1h) and 'Log Source' = 'VCN Flow Logs' and 'Action' = 'BLOCK' | stats COUNT by 'Destination Port' | sort -COUNT"

Maintenance Checklist
- Keep REST endpoints and SDK mappings aligned with latest Oracle docs.
- Validate query_enhancer rules as LA syntax evolves (quoting, operators).
- Ensure namespace resolution prefers Log Analytics namespace; fall back to Object Storage namespace only if necessary.
- Enforce consistent region handling across services when correlating Monitoring/Compute/LA.
