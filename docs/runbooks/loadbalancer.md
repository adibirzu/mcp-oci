# Load Balancer MCP Server Runbook (oci-mcp-loadbalancer)

Use this runbook for load balancer inventory and provisioning checks.

## Inputs
- Compartment OCID or name
- Load balancer display name (optional)
- Region (optional if default)

## Steps
1. **List load balancers**
   - Tool: `list_load_balancers`
2. **Identify target load balancer**
   - Tool: `list_load_balancers` (match display name)
3. **Create a load balancer if requested**
   - Tool: `create_load_balancer`
4. **Re-list to confirm lifecycle state**
   - Tool: `list_load_balancers`

## Skill/Tool mapping
- Inventory: `list_load_balancers`
- Provisioning: `create_load_balancer`

## Outputs
- Load balancer list with state and shape
- Confirmation of provisioning
