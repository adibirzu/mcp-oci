# Unified MCP Server Runbook (oci-mcp-unified)

Use this runbook when the client wants a single endpoint with multiple skills/tools.

## Inputs
- Target domain (compute, network, security, cost, inventory)
- Compartment OCID or name
- Time window (if cost or logs)

## Steps
1. **Discover available tools**
   - Resource: `server://manifest`
2. **Select the relevant skill cluster**
   - Prefer the skill tool when available (cost analysis, inventory audit, network diagnostics)
3. **Run the primary skill/tool**
   - Example: cost analysis, inventory audit, network diagnostics
4. **Follow up with a service-specific tool if needed**
   - Example: compute list, security list, database list
5. **Summarize results with next actions**

## Skill/Tool mapping
- Skill discovery: `server://manifest`
- Cost skill: use cost tools exposed by unified
- Inventory skill: use inventory tools exposed by unified
- Network diagnostics: use network tools exposed by unified

## Outputs
- Single-server workflow results
- Recommended next actions and optional deep dives
