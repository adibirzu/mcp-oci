# Database MCP Server Runbook (oci-mcp-db)

Use this runbook for Autonomous Database and DB system inventory plus health checks.

## Inputs
- Compartment OCID or name
- Database OCID or display name (optional)
- Region (optional if default)

## Steps
1. **List Autonomous Databases and DB systems**
   - Tools: `list_autonomous_databases`, `list_db_systems`
2. **Get database details**
   - Tool: `get_autonomous_database`
3. **Collect performance snapshots**
   - Tools: `get_db_cpu_snapshot`, `get_db_metrics`
4. **Lifecycle action if requested**
   - Tools: `start_autonomous_database`, `stop_autonomous_database`, `restart_autonomous_database`
   - Tools: `start_db_system`, `stop_db_system`, `restart_db_system`
5. **Multi-cloud cost checks (if configured)**
   - Tools: `query_multicloud_costs`, `get_cost_summary_by_cloud`

## Skill/Tool mapping
- Inventory: `list_autonomous_databases`, `list_db_systems`
- Details: `get_autonomous_database`
- Performance: `get_db_cpu_snapshot`, `get_db_metrics`
- Lifecycle: `start_autonomous_database`, `stop_autonomous_database`, `restart_autonomous_database`, `start_db_system`, `stop_db_system`, `restart_db_system`
- Cost: `query_multicloud_costs`, `get_cost_summary_by_cloud`

## Outputs
- Database inventory and lifecycle state
- Performance snapshot and anomalies
- Confirmation of lifecycle actions
