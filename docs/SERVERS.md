# MCP OCI Servers Index

This repository hosts MCP servers for common OCI services. Each server follows MCP best practices and FastMCP framework guidelines, exposing tools as `oci:<service>:<action>`.

- mcp_oci_iam — Identity and Access Management
- mcp_oci_compute — Compute (with creation capabilities)
- mcp_oci_objectstorage — Object Storage
- mcp_oci_networking — Virtual Cloud Network (VCN) (with creation capabilities)
- mcp_oci_blockstorage — Block Volumes (with creation capabilities)
- mcp_oci_loadbalancer — Load Balancer (with creation capabilities)
- mcp_oci_filestorage — File Storage
- mcp_oci_dns — DNS
- mcp_oci_apigateway — API Gateway
- mcp_oci_database — Database (Autonomous)
- mcp_oci_oke — Container Engine for Kubernetes (OKE)
- mcp_oci_functions — Functions
- mcp_oci_logging — Logging
- mcp_oci_monitoring — Monitoring
- mcp_oci_events — Events
- mcp_oci_streaming — Streaming
- mcp_oci_ons — Notifications (ONS)
- mcp_oci_vault — Vault (Secrets)
- mcp_oci_kms — Key Management (KMS)
- mcp_oci_resourcemanager — Resource Manager
- mcp_oci_usageapi — Usage API (Cost & Usage)
- mcp_oci_budgets — Budgets (Cost Control)
- mcp_oci_limits — Limits and Quotas (Cost Control)
- oci-mcp-observability — Observability and Log Analytics (preferred entry)
- mcp_oci_osub — Subscriptions (OSUB)
- mcp_oci_inventory — Inventory Management (with compute capacity reporting)
- mcp_oci_security — Security Services
- mcp_oci_observability — Observability and Management
- mcp_oci_cost — Cost Management

See each package under `mcp_servers/` for implementation details and available tools.

---

Log Analytics (canonical Logan queries)

Preferred entry: oci-mcp-observability (wraps the consolidated Log Analytics implementation).

- Canonical query: sources in last 24h
  * Logan query:
    * | where Time > dateRelative(24h) | stats COUNT as logrecords by 'Log Source' | sort -logrecords | head 100
  * Tool to use:
    - execute_logan_query (oci-mcp-observability)
  * Example call (JSON args):
    {
      "query": "* | where Time > dateRelative(24h) | stats COUNT as logrecords by 'Log Source' | sort -logrecords | head 100",
      "time_range": "24h"
    }

Notes:
- COUNT is accepted by OCI LA as COUNT with optional (<fieldName>). If your environment rejects COUNT() without an argument, use COUNT as in the example above.
- Always quote field names that contain spaces, e.g. 'Log Source'.
- Prefer adding an explicit Time > dateRelative(...) filter for performance.

Troubleshooting quick checks (oci-mcp-observability):
- check_oci_connection: Verifies namespace resolution and runs a test query (* | head 1) over 1h.
- quick_checks: Runs 3 small queries (head, fields, stats_by_source) to validate permissions and ingestion quickly.

Monitoring (OCI Metrics) canonical usage

Preferred entry: mcp_oci_monitoring.

- Summarize metrics data (CPU mean @ 1m):
  * Namespace: oci_computeagent
  * Query: CpuUtilization[1m].mean()
  * Use either:
    - oci_monitoring_summarize_metrics with start_time/end_time (UTC ISO8601)
    - oci_monitoring_summarize_metrics_window with window like 1h/24h (auto-resolution)

Example (window wrapper):
{
  "compartment_id": "[Link to Secure Variable: OCI_COMPARTMENT_OCID]",
  "namespace": "oci_computeagent",
  "query": "CpuUtilization[1m].mean()",
  "window": "1h"
}

Observability telemetry

All MCP servers initialize OTEL tracing and metrics:
- Traces/metrics exported to the endpoint in OTEL_EXPORTER_OTLP_ENDPOINT (default wiring in mcp.json to http://localhost:4317).
- Prometheus /metrics port can be set via METRICS_PORT (each server enables it when run as __main__).
- See docs/macos-observability-setup.md for a full-stack local setup (Grafana, Prometheus, Tempo, Pyroscope) and verification steps.
