Inventory MCP Server (oci-mcp-inventory) - SDK/REST Reference and Discovery Guide

Overview
- Purpose: Inventory and discovery across regions/compartments using the OCI Python SDK; convenience wrappers over per-service MCP servers and ShowOCI helper for human-readable diffs.
- FASTMCP readiness:
  - Tracing/metrics: tool_span with OTEL attributes; optional Prometheus /metrics.
  - Caching: Disk+memory caching with TTL and diff support for ShowOCI output.
- Primitives:
  - Instance detail (id, display_name, shape, lifecycle_state, AD, time_created, IPs).
  - Resource discovery lists per type: VCNs, Subnets, Security Lists, Load Balancers, Functions Apps, Streams.

Core Tools and API Mappings

1) run_showoci
- What it does: Executes third-party ShowOCI script to produce a comprehensive inventory with optional diff between runs.
- Inputs: profile, regions[], compartments[], resource_types[], diff_mode, limit, force_refresh.
- Behavior: Orchestrates a subprocess call; not an SDK call itself. Used for human-readable reporting and change-diffing across runs.
- Reference: https://github.com/oracle/oci-python-sdk/tree/master/examples/showoci
- Notes: Does not replace precise SDK enumeration in per-service tools; used for quick audit/diff.

2) run_showoci_simple
- Convenience wrapper with comma-separated strings mapping to run_showoci.

3) generate_compute_capacity_report
- What it does: Compiles compute capacity/utilization view and recommendations; enumerates instances and VNICs, builds IP map and summaries.
- SDK calls:
  - oci.core.ComputeClient.list_instances
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.ComputeClient.html#oci.core.ComputeClient.list_instances
  - oci.core.ComputeClient.list_vnic_attachments
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.ComputeClient.html#oci.core.ComputeClient.list_vnic_attachments
  - oci.core.VirtualNetworkClient.get_vnic
    - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.VirtualNetworkClient.html#oci.core.VirtualNetworkClient.get_vnic
  - oci.monitoring.MonitoringClient (optionally for utilization, currently not fetched when include_metrics=false)
    - summarize_metrics_data:
      https://docs.oracle.com/en-us/iaas/tools/python/latest/api/monitoring/client/oci.monitoring.MonitoringClient.html#oci.monitoring.MonitoringClient.summarize_metrics_data
- Notes: Adds note for stopped instances with released public IPs; groups by shape/state/AD; limits instance_details slice to 50 for performance.

4) list_all_discovery
- What it does: Aggregated discovery of networking + compute + LB + functions + streaming; returns counts and small samples (limit_per_type).
- Underlying per-service calls (via MCP servers):
  - Networking:
    - VCNs: oci.core.VirtualNetworkClient.list_vcns
      https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.VirtualNetworkClient.html#oci.core.VirtualNetworkClient.list_vcns
    - Subnets: oci.core.VirtualNetworkClient.list_subnets
      https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.VirtualNetworkClient.html#oci.core.VirtualNetworkClient.list_subnets
    - Security Lists: oci.core.VirtualNetworkClient.list_security_lists
      https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.VirtualNetworkClient.html#oci.core.VirtualNetworkClient.list_security_lists
  - Compute:
    - Instances: oci.core.ComputeClient.list_instances
      https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.ComputeClient.html#oci.core.ComputeClient.list_instances
  - Load Balancer:
    - oci.load_balancer.LoadBalancerClient.list_load_balancers
      https://docs.oracle.com/en-us/iaas/tools/python/latest/api/load_balancer/client/oci.load_balancer.LoadBalancerClient.html#oci.load_balancer.LoadBalancerClient.list_load_balancers
  - Functions:
    - oci.functions.FunctionsManagementClient.list_applications
      https://docs.oracle.com/en-us/iaas/tools/python/latest/api/functions/client/oci.functions.FunctionsManagementClient.html#oci.functions.FunctionsManagementClient.list_applications
  - Streaming:
    - oci.streaming.StreamAdminClient.list_streams
      https://docs.oracle.com/en-us/iaas/tools/python/latest/api/streaming/client/oci.streaming.StreamAdminClient.html#oci.streaming.StreamAdminClient.list_streams
- Notes: Each sub-call is wrapped and safe-serialized to avoid returning raw SDK objects. Uses small sample sizes for UX speed.

5) list_streams_inventory
- What it does: Lists OCI Streaming streams in a compartment.
- SDK call: oci.streaming.StreamAdminClient.list_streams
  - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/streaming/client/oci.streaming.StreamAdminClient.html#oci.streaming.StreamAdminClient.list_streams

6) list_functions_applications_inventory
- What it does: Lists OCI Functions applications.
- SDK call: oci.functions.FunctionsManagementClient.list_applications
  - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/functions/client/oci.functions.FunctionsManagementClient.html#oci.functions.FunctionsManagementClient.list_applications

7) list_security_lists_inventory
- What it does: Lists security lists (or NSGs) in a compartment/VCN.
- SDK call: oci.core.VirtualNetworkClient.list_security_lists
  - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/core/client/oci.core.VirtualNetworkClient.html#oci.core.VirtualNetworkClient.list_security_lists

8) list_load_balancers_inventory
- What it does: Lists Load Balancers in a compartment.
- SDK call: oci.load_balancer.LoadBalancerClient.list_load_balancers
  - https://docs.oracle.com/en-us/iaas/tools/python/latest/api/load_balancer/client/oci.load_balancer.LoadBalancerClient.html#oci.load_balancer.LoadBalancerClient.list_load_balancers

Pagination & Caching
- Pagination: All list_* operations rely on SDK pagination helpers upstream (list_call_get_all_results) or server-side paging in submodules to reliably enumerate resources.
  - Pagination guide:
    https://docs.oracle.com/en-us/iaas/tools/python/latest/sdk_behaviors/pagination.html
- Caching: get_cache().get_or_refresh used for expensive operations; TTL defaults applied per tool; ShowOCI output diffed and rotated in /tmp/mcp-oci-cache/inventory.

Region & Compartment Resolution
- Region: Resolved from config; can be overridden per-call.
- Compartment: Defaults to tenancy OCID when not provided, via get_oci_config(profile_name=...), or via COMPARTMENT_OCID environment variable where appropriate.

REST (Signed) Fallbacks
- Not generally required for inventory enumeration since SDK coverage is sufficient. If needed, use oci.signer.Signer with requests to call Core/Networking endpoints directly:
  - Signer guide: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/pythonsdk.htm
  - REST index: https://docs.oracle.com/en-us/iaas/api/

Correlation Recipes (Inventory + Metrics + Logs)
- Instances → IPs:
  - Use generate_compute_capacity_report to enumerate instance IDs and IPs.
- CPU spikes:
  - Monitoring SDK: summarize_metrics_data per instance to find high CPU windows.
- Logs/Flow:
  - Use Log Analytics execute_query to filter by Time window and IP/resourceId and correlate flows/events.

Troubleshooting
- Empty results:
  - Confirm compartment/region inputs; ensure IAM policies grant read for listed resources.
- Throttling:
  - Enable caching where applicable; lower limit_per_type; restrict resource_types in ShowOCI.
- Serialization errors:
  - The server uses a safe serializer; if issues persist, ensure SDK object versions align with pinned SDK in this repo.

Maintenance Checklist
- Verify SDK surfaces used by per-service MCP wrappers remain stable.
- Keep ShowOCI path resolution robust relative to repo root.
- Ensure privacy masking/wrappers remain applied in __main__.
- Validate TTLs and diff behavior do not leak sensitive data to disk in shared environments.
