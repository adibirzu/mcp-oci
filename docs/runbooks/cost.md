# Cost MCP Server Runbook (oci-mcp-cost)

Use this runbook for cost questions by tenancy, compartment, resource, database, or tags.

## Inputs
- Time window (start/end or days)
- Tenancy OCID
- Optional: compartment OCID or name
- Optional: service, resource, database, tag key/value

## Steps
1. **Total cost summary**
   - Tool: `get_cost_summary`
2. **Cost by compartment or service**
   - Tools: `cost_by_compartment_daily`, `service_cost_drilldown`
3. **Resource-level spend**
   - Tool: `cost_by_resource`
4. **Database and PDB spend**
   - Tools: `cost_by_database`, `cost_by_pdb`
5. **Tag attribution**
   - Tools: `list_tag_defaults`, `cost_by_tag_key_value`
6. **Trends, budgets, anomalies**
   - Tools: `monthly_trend_forecast`, `budget_status_and_actions`, `detect_cost_anomaly`

## Skill/Tool mapping
- Summary: `get_cost_summary`
- Compartment/service: `cost_by_compartment_daily`, `service_cost_drilldown`
- Resource detail: `cost_by_resource`
- DB/PDB: `cost_by_database`, `cost_by_pdb`
- Tags: `list_tag_defaults`, `cost_by_tag_key_value`
- Trend/budget: `monthly_trend_forecast`, `budget_status_and_actions`, `detect_cost_anomaly`

## Outputs
- Cost breakdown with currency
- Top drivers and variance
- Budget status and optimization notes
