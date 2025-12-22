# Compute MCP Server Runbook (oci-mcp-compute)

Use this runbook for instance inventory, lifecycle actions, and CPU health checks.

## Inputs
- Compartment OCID or name
- Region (optional if default)
- Instance OCID or display name (optional)

## Steps
1. **List instances in scope**
   - Tool: `list_instances`
2. **Get instance details + IPs for the target**
   - Tool: `get_instance_details_with_ips`
3. **Fetch recent CPU metrics for hot instances**
   - Tool: `get_instance_metrics`
4. **Lifecycle action if requested (start/stop/restart)**
   - Tools: `start_instance`, `stop_instance`, `restart_instance`
5. **Validate post-action state**
   - Tool: `list_instances`
6. **Escalate for network or log analysis if needed**
   - Use `oci-mcp-network` or `oci-mcp-loganalytics` runbooks

## Skill/Tool mapping
- Inventory: `list_instances`
- Details: `get_instance_details_with_ips`
- Metrics: `get_instance_metrics`
- Actions: `start_instance`, `stop_instance`, `restart_instance`

## Outputs
- Instance list with lifecycle, shape, IPs
- CPU summary and status
- Confirmation of lifecycle actions
