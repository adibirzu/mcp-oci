Compute MCP Server (oci-mcp-compute) - SDK and API Reference

Overview
- Purpose: Provide black-box tools to interact with OCI Compute instances via the official OCI Python SDK, with optional REST fallbacks using signed requests.
- Primitives:
  - Instance summary: {id, display_name, lifecycle_state, shape, availability_domain, compartment_id, time_created, private/public IPs}
  - Metrics summary: {average, max, min, datapoints_count} over a time window
- Observability: Tools run in traced spans with OTEL attributes for backend calls; Prometheus /metrics optional via env.

FASTMCP Readiness
- Healthcheck tool: Lightweight liveness/readiness
- Doctor tool: Config summary, privacy masking, tool list
- Caching: Shared cache layer used for list_instances to reduce API pressure
- Pagination: Uses oci.pagination.list_call_get_all_results to retrieve all pages per OCI best practices

Tools and Mappings

1) list_instances
- What it does: Returns instances in a compartment (defaults to resolved COMPARTMENT_OCID), with optional region override and lifecycle_state filter. Enhances with IPs if instance is RUNNING.
- SDK calls:
  - oci.core.ComputeClient.list_instances
    - Python SDK docs:
      https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.ComputeClient.html#oci.core.ComputeClient.list_instances
  - oci.core.ComputeClient.get_instance (when enriching IPs)
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.ComputeClient.html#oci.core.ComputeClient.get_instance
  - oci.core.VirtualNetworkClient.get_vnic (to resolve IPs)
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.VirtualNetworkClient.html#oci.core.VirtualNetworkClient.get_vnic
  - Pagination: oci.pagination.list_call_get_all_results
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/sdk_behaviors/pagination.html
- REST references (optional alternative):
  - ListInstances (Core): https://docs.oracle.com/en-us/iaas/api/#/en/iaas/20160918/Instance/ListInstances
  - GetInstance (Core): https://docs.oracle.com/en-us/iaas/api/#/en/iaas/20160918/Instance/GetInstance
  - GetVnic (Core): https://docs.oracle.com/en-us/iaas/api/#/en/iaas/20160918/Vnic/GetVnic
- Notes:
  - lifecycle_state validated against known values (RUNNING, STOPPED, etc.)
  - Region can be overridden per-call; underlying clients are created via a common get_client wrapper.

2) get_instance_details_with_ips
- What it does: Returns a detailed instance document including primary/all IP addresses.
- SDK calls:
  - oci.core.ComputeClient.get_instance
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.ComputeClient.html#oci.core.ComputeClient.get_instance
  - oci.core.VirtualNetworkClient.get_vnic
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.VirtualNetworkClient.html#oci.core.VirtualNetworkClient.get_vnic
  - oci.core.ComputeClient.list_vnic_attachments (via pagination)
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.ComputeClient.html#oci.core.ComputeClient.list_vnic_attachments
- REST references:
  - GetInstance: https://docs.oracle.com/en-us/iaas/api/#/en/iaas/20160918/Instance/GetInstance
  - ListVnicAttachments: https://docs.oracle.com/en-us/iaas/api/#/en/iaas/20160918/VnicAttachment/ListVnicAttachments
  - GetVnic: https://docs.oracle.com/en-us/iaas/api/#/en/iaas/20160918/Vnic/GetVnic

3) get_instance_metrics
- What it does: Returns CPU utilization summary for an instance over a window (default 1h).
- SDK calls:
  - oci.monitoring.MonitoringClient.summarize_metrics_data
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/monitoring/client/oci.monitoring.MonitoringClient.html#oci.monitoring.MonitoringClient.summarize_metrics_data
  - Prior lookup: oci.core.ComputeClient.get_instance (to resolve compartment_id)
- REST references:
  - SummarizeMetricsData (Monitoring): https://docs.oracle.com/en-us/iaas/api/#/en/monitoring/20180401/MetricData/SummarizeMetricsData

4) start_instance
- What it does: Starts a compute instance (requires ALLOW_MUTATIONS=true).
- SDK calls:
  - oci.core.ComputeClient.instance_action with action="START"
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.ComputeClient.html#oci.core.ComputeClient.instance_action
- REST references:
  - InstanceAction: https://docs.oracle.com/en-us/iaas/api/#/en/iaas/20160918/InstanceAction/InstanceAction

5) stop_instance
- What it does: Stops a compute instance (requires ALLOW_MUTATIONS=true).
- SDK calls:
  - oci.core.ComputeClient.instance_action with action="STOP"
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.ComputeClient.html#oci.core.ComputeClient.instance_action
- REST references:
  - InstanceAction: https://docs.oracle.com/en-us/iaas/api/#/en/iaas/20160918/InstanceAction/InstanceAction

6) restart_instance
- What it does: Restarts a compute instance; soft reset by default or hard reset if requested (requires ALLOW_MUTATIONS=true).
- SDK calls:
  - oci.core.ComputeClient.instance_action with action="SOFTRESET" or "RESET"
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.ComputeClient.html#oci.core.ComputeClient.instance_action
- REST references:
  - InstanceAction: https://docs.oracle.com/en-us/iaas/api/#/en/iaas/20160918/InstanceAction/InstanceAction

7) healthcheck
- What it does: Returns basic readiness/liveness info.

8) doctor
- What it does: Returns configuration summary (profile, region), privacy mask status, and tool list.

Inputs and Behavior
- Region override: list_instances and other tools accept region overrides and will create region-scoped clients via a shared get_client wrapper for consistency and reuse.
- Compartment resolution: If compartment_id is not provided, the server resolves it with get_compartment_id() which typically reads COMPARTMENT_OCID or falls back to tenancy where appropriate.
- Pagination: All list operations use list_call_get_all_results to ensure full enumeration across pages, consistent with SDK best practices.
- Caching: list_instances results are cached per parameter set with an opt-out via force_refresh.

REST Fallback (Signed Requests)
- When to use: For features not present in the SDK layer or for composite flows where REST provides a better shape, an OCI RequestSigner can be used to sign requests to Core/Monitoring endpoints.
- Reference:
  - Python SDK Signer guide: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/pythonsdk.htm
  - REST API index: https://docs.oracle.com/en-us/iaas/api/

Operational Notes
- OTEL tracing: Each tool wraps calls in a tool_span with attributes for oci_service, operation, region, and backend endpoint (when available). OPC request IDs are attached to spans when present.
- Privacy masking: If privacy is enabled, outputs are redacted via a common wrapper.
- Metrics: Optional Prometheus exporter listens on METRICS_PORT (default 8001) when enabled.

Examples (Pseudo-usage)
- List instances (all states):
  - Tool: list_instances
  - Params: {"compartment_id": null, "region": null, "lifecycle_state": null}
- Get instance details with IPs:
  - Tool: get_instance_details_with_ips
  - Params: {"instance_id": "ocid1.instance..."}
- CPU metrics last hour:
  - Tool: get_instance_metrics
  - Params: {"instance_id": "ocid1.instance...", "window": "1h"}

Maintenance Checklist
- Verify SDK calls map 1:1 to latest Python SDK docs and that parameters/options are up to date.
- Validate lifecycle_state enum set when SDK updates add/remove states.
- Ensure pagination behavior remains consistent with SDK guidance.
- Confirm signer-based REST example remains accurate when REST API evolves.
