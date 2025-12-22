# Block Storage MCP Server Runbook (oci-mcp-blockstorage)

Use this runbook for block volume inventory and provisioning requests.

## Inputs
- Compartment OCID or name
- Availability domain (optional)
- Volume display name (optional)

## Steps
1. **List block volumes in scope**
   - Tool: `list_volumes`
2. **Check existing volume metadata**
   - Tool: `list_volumes` (filter by display name)
3. **Create a volume if requested**
   - Tool: `create_volume`
4. **Validate the new volume state**
   - Tool: `list_volumes`

## Skill/Tool mapping
- Inventory: `list_volumes`
- Provisioning: `create_volume`

## Outputs
- Volume list with size/state
- Confirmation of created volume
