# OCI MCP Compute Server

This MCP server provides tools for managing OCI Compute instances.

## Tools

- list_instances: List compute instances in a compartment.
- start_instance: Start a specific instance (requires ALLOW_MUTATIONS=true).
- stop_instance: Stop a specific instance (requires ALLOW_MUTATIONS=true).
- get_instance_metrics: Get CPU utilization metrics summary for an instance.

## Running the Server

```bash
python -m mcp_servers.compute.server
```

## Environment Variables

- OCI_PROFILE: OCI config profile (default: DEFAULT)
- OCI_REGION: OCI region
- COMPARTMENT_OCID: Default compartment OCID
- ALLOW_MUTATIONS: Set to 'true' to enable start/stop actions (default: false)

## Tracing

The server is instrumented with OpenTelemetry tracing, exporting to OTLP endpoint at http://localhost:4317.
