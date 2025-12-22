# Inventory MCP Server Runbook (oci-mcp-inventory)

Use this runbook for tenancy/compartment asset discovery and baseline reports.

## Inputs
- Compartment OCID or name
- Region list (optional)
- Resource type filters (optional)

## Steps
1. **Run a quick discovery sweep**
   - Tool: `list_all_discovery`
2. **Generate a full ShowOCI report**
   - Tools: `run_showoci`, `run_showoci_simple`
3. **Targeted inventories for key services**
   - Tools: `list_load_balancers_inventory`, `list_security_lists_inventory`, `list_streams_inventory`, `list_functions_applications_inventory`
4. **Compute capacity overview**
   - Tool: `generate_compute_capacity_report`
5. **Summarize inventory and deltas**
   - Compare with previous cache snapshots if available

## Skill/Tool mapping
- Baseline discovery: `list_all_discovery`
- Full inventory: `run_showoci`, `run_showoci_simple`
- Service-specific inventories: `list_load_balancers_inventory`, `list_security_lists_inventory`, `list_streams_inventory`, `list_functions_applications_inventory`
- Capacity insights: `generate_compute_capacity_report`

## Outputs
- Inventory report with counts by service
- Capacity recommendations
- Drift/delta notes when comparing snapshots
