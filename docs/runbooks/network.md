# Network MCP Server Runbook (oci-mcp-network)

Use this runbook for VCN inventory, subnet checks, and public endpoint visibility.

## Inputs
- Compartment OCID or name
- VCN name or OCID (optional)
- Region (optional if default)

## Steps
1. **List VCNs in scope**
   - Tool: `list_vcns`
2. **Enumerate subnets in the VCN**
   - Tool: `list_subnets`
3. **Summarize public endpoints**
   - Tool: `summarize_public_endpoints`
4. **Provision VCN + subnets when requested**
   - Tools: `create_vcn`, `create_subnet`, `create_vcn_with_subnets`, `create_vcn_with_subnets_rest`
5. **Validate connectivity dependencies**
   - Use `oci-mcp-compute` or `oci-mcp-loadbalancer` runbooks if needed

## Skill/Tool mapping
- VCN inventory: `list_vcns`
- Subnets: `list_subnets`
- Public exposure: `summarize_public_endpoints`
- Provisioning: `create_vcn`, `create_subnet`, `create_vcn_with_subnets`, `create_vcn_with_subnets_rest`

## Outputs
- VCN topology summary
- Public endpoint inventory
- Targeted remediation suggestions
