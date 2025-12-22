# Log Analytics MCP Server Runbook (oci-mcp-loganalytics)

Use this runbook for Logging Analytics queries, MITRE mapping, and log triage.

## Inputs
- Compartment OCID or name
- Time range (minutes or absolute)
- Query intent (error, auth, network, security)

## Steps
1. **Validate Logging Analytics connectivity**
   - Tool: `check_oci_connection`
2. **Build or validate the query**
   - Tools: `validate_query`, `get_documentation`
3. **Execute the query**
   - Tool: `execute_query`
4. **Security triage (if requested)**
   - Tools: `search_security_events`, `get_mitre_techniques`
5. **Stats or advanced analytics**
   - Tools: `perform_statistical_analysis`, `perform_advanced_analytics`
6. **IP activity drilldown**
   - Tool: `analyze_ip_activity`

## Skill/Tool mapping
- Connectivity: `check_oci_connection`
- Query validation: `validate_query`, `get_documentation`
- Query execution: `execute_query`
- Security mapping: `search_security_events`, `get_mitre_techniques`
- Analytics: `perform_statistical_analysis`, `perform_advanced_analytics`
- IP drilldown: `analyze_ip_activity`

## Outputs
- Executed query results and statistics
- MITRE technique mapping (if applicable)
- Recommended follow-up actions
