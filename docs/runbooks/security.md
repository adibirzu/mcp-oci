# Security MCP Server Runbook (oci-mcp-security)

Use this runbook for IAM inventory and Cloud Guard/Data Safe findings review.

## Inputs
- Tenancy OCID
- Compartment OCID (optional)

## Steps
1. **List compartments for scope confirmation**
   - Tool: `list_compartments`
2. **Review IAM users, groups, and policies**
   - Tools: `list_iam_users`, `list_groups`, `list_policies`
3. **Review Cloud Guard problems**
   - Tool: `list_cloud_guard_problems`
4. **Review Data Safe findings (if enabled)**
   - Tool: `list_data_safe_findings`
5. **Summarize high-risk findings and next actions**
   - Provide remediation guidance and escalation if needed

## Skill/Tool mapping
- IAM inventory: `list_iam_users`, `list_groups`, `list_policies`
- Findings: `list_cloud_guard_problems`, `list_data_safe_findings`
- Scope validation: `list_compartments`

## Outputs
- IAM inventory summary
- Findings list with severity
- Recommended remediation actions
