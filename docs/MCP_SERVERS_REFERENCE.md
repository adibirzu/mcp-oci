# MCP Servers Reference Documentation

> **Last Updated**: December 17, 2025
> **Test Status**: All 15 servers passing, 273 tools available

## Overview

This document provides comprehensive documentation for all MCP (Model Context Protocol) servers in the OCI MCP ecosystem. These servers provide tools for interacting with Oracle Cloud Infrastructure services through a standardized protocol.

## Quick Reference

| Server | Tools | Category | Description |
|--------|-------|----------|-------------|
| oci-compute | 9 | Infrastructure | Compute instance management |
| oci-network | 9 | Infrastructure | VCN and subnet management |
| oci-blockstorage | 4 | Storage | Block volume management |
| oci-objectstorage | 10 | Storage | Object storage and buckets |
| oci-loadbalancer | 4 | Infrastructure | Load balancer management |
| oci-db | 27 | Database | Database operations and management |
| oci-cost | 24 | FinOps | Cost analysis and optimization |
| oci-security | 8 | Security | IAM and security management |
| oci-observability | 29 | Observability | Log analytics and monitoring |
| oci-inventory | 13 | Discovery | Resource inventory and discovery |
| oci-agents | 18 | AI/ML | GenAI Agent management |
| oci-loganalytics | 2 | Observability | Log analytics queries |
| oci-unified | 65 | Unified | All capabilities in one server |
| finopsai | 12 | FinOps | Advanced cost intelligence |
| opsi | 39 | Database | Operations Insights |

---

## Server Details

### 1. oci-compute (9 tools)

**Purpose**: Manage OCI compute instances - list, create, start, stop, restart instances and get metrics.

#### Tools:
- `healthcheck` - Check server health
- `doctor` - Diagnose issues
- `list_instances` - List compute instances in a compartment
- `create_instance` - Create a new compute instance
- `start_instance` - Start a stopped instance
- `stop_instance` - Stop a running instance
- `restart_instance` - Restart an instance
- `get_instance_metrics` - Get CPU, memory, network metrics
- `get_instance_details_with_ips` - Get instance details including IP addresses

#### Usage via Gateway:
```bash
# List instances
curl -X POST http://localhost:8080/servers/oci-compute/tools/list_instances \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"compartment_id": "ocid1.compartment..."}}'
```

---

### 2. oci-network (9 tools)

**Purpose**: Manage OCI networking resources including VCNs, subnets, and public endpoints.

#### Tools:
- `healthcheck` - Check server health
- `doctor` - Diagnose issues
- `list_vcns` - List Virtual Cloud Networks
- `create_vcn` - Create a new VCN
- `list_subnets` - List subnets in a VCN
- `create_subnet` - Create a new subnet
- `summarize_public_endpoints` - Get summary of public endpoints
- `create_vcn_with_subnets` - Create VCN with subnets in one call
- `create_vcn_with_subnets_rest` - REST-based VCN creation

---

### 3. oci-blockstorage (4 tools)

**Purpose**: Manage OCI block storage volumes.

#### Tools:
- `healthcheck` - Check server health
- `list_volumes` - List block volumes
- `create_volume` - Create a new block volume
- `doctor` - Diagnose issues

---

### 4. oci-objectstorage (10 tools)

**Purpose**: Manage OCI Object Storage buckets, objects, and database backups.

#### Tools:
- `healthcheck` - Check server health
- `doctor` - Diagnose issues
- `list_buckets` - List storage buckets
- `get_bucket` - Get bucket details
- `list_objects` - List objects in a bucket
- `get_bucket_usage` - Get bucket usage statistics
- `get_storage_report` - Generate storage report
- `list_db_backups` - List database backups in Object Storage
- `get_backup_details` - Get backup details
- `create_preauthenticated_request` - Create PAR for object access

---

### 5. oci-loadbalancer (4 tools)

**Purpose**: Manage OCI Load Balancers.

#### Tools:
- `healthcheck` - Check server health
- `list_load_balancers` - List load balancers
- `create_load_balancer` - Create a new load balancer
- `doctor` - Diagnose issues

---

### 6. oci-db (27 tools)

**Purpose**: Comprehensive database management including Autonomous DB, DB Systems, and multi-cloud cost analysis.

#### Tools:
- `healthcheck` / `doctor` - Health and diagnostics
- **Autonomous Database**: `list_autonomous_databases`, `start_autonomous_database`, `stop_autonomous_database`, `restart_autonomous_database`, `get_autonomous_database`
- **DB Systems**: `list_db_systems`, `start_db_system`, `stop_db_system`, `restart_db_system`
- **Metrics**: `get_db_cpu_snapshot`, `get_db_metrics`
- **Multi-cloud Costs**: `query_multicloud_costs`, `get_cost_summary_by_cloud`
- **Skills**: Cost analysis, infrastructure discovery, capacity reports, network analysis

---

### 7. oci-cost (24 tools)

**Purpose**: FinOps and cost management - analyze costs, detect anomalies, forecast spending.

#### Tools:
- `doctor` / `healthcheck` - Health and diagnostics
- **Tenancy Info**: `get_tenancy_info`, `get_cache_stats`, `refresh_local_cache`
- **Cost Analysis**:
  - `cost_by_compartment_daily` - Daily cost by compartment
  - `service_cost_drilldown` - Service-level cost breakdown
  - `cost_by_tag_key_value` - Cost grouped by tags
  - `monthly_trend_forecast` - Monthly cost forecast
- **FinOps Reports**:
  - `budget_status_and_actions` - Budget tracking
  - `schedule_report_create_or_list` - Scheduled reports
  - `object_storage_costs_and_tiering` - Storage cost optimization
  - `top_cost_spikes_explain` - Anomaly explanation
  - `per_compartment_unit_cost` - Unit cost analysis
  - `forecast_vs_universal_credits` - Credit forecasting
- **Skills**: Analyze cost trends, detect anomalies, service breakdown, optimization reports

---

### 8. oci-security (8 tools)

**Purpose**: IAM and security management - users, groups, policies, Cloud Guard, Data Safe.

#### Tools:
- `healthcheck` / `doctor` - Health and diagnostics
- `list_compartments` - List compartments
- `list_iam_users` - List IAM users
- `list_groups` - List IAM groups
- `list_policies` - List IAM policies
- `list_cloud_guard_problems` - List security problems
- `list_data_safe_findings` - Data Safe security findings

---

### 9. oci-observability (29 tools)

**Purpose**: Comprehensive observability - Log Analytics, OpenTelemetry, security event correlation.

#### Tools:
- **Log Analytics Namespace**: `list_la_namespaces`, `set_la_namespace`, `get_la_namespace`
- **Query Execution**: `run_log_analytics_query`, `run_saved_search`, `build_advanced_query`, `validate_query`
- **Security Analysis**: `correlate_threat_intelligence`, `search_security_events`, `get_mitre_techniques`, `analyze_ip_activity`
- **Advanced Analytics**: `execute_statistical_analysis`, `execute_advanced_analytics`, `correlate_metrics_with_logs`
- **OpenTelemetry**: `get_mcp_otel_capabilities`, `create_traced_operation`, `send_test_trace_notification`, `analyze_trace_correlation`
- **Diagnostics**: `diagnostics_loganalytics_stats`, `doctor`, `doctor_all`

---

### 10. oci-inventory (13 tools)

**Purpose**: Infrastructure discovery and inventory - ShowOCI, capacity reports, resource listing.

#### Tools:
- `healthcheck` / `doctor` - Health and diagnostics
- `get_tenancy_info` / `get_cache_stats` / `refresh_local_cache` - Cache management
- `run_showoci` / `run_showoci_simple` - ShowOCI integration
- `generate_compute_capacity_report` - Compute capacity analysis
- `list_streams_inventory` - Streaming service inventory
- `list_functions_applications_inventory` - Functions inventory
- `list_security_lists_inventory` - Security list inventory
- `list_load_balancers_inventory` - Load balancer inventory
- `list_all_discovery` - Full resource discovery

---

### 11. oci-agents (18 tools)

**Purpose**: Manage OCI GenAI Agents, endpoints, and knowledge bases.

#### Tools:
- **Agent Management**: `list_agents`, `create_agent`, `get_agent`, `update_agent`, `delete_agent`
- **Agent Endpoints**: `create_agent_endpoint`, `list_agent_endpoints`, `get_agent_endpoint`, `update_agent_endpoint`, `delete_agent_endpoint`
- **Knowledge Bases**: `create_knowledge_base`, `list_knowledge_bases`, `get_knowledge_base`, `update_knowledge_base`, `delete_knowledge_base`
- **Testing**: `test_agent_message` - Send test message to agent

---

### 12. oci-loganalytics (2 tools)

**Purpose**: Basic Log Analytics health and diagnostics.

#### Tools:
- `healthcheck` - Check Log Analytics connection
- `doctor` - Diagnose Log Analytics issues

---

### 13. oci-unified (65 tools)

**Purpose**: Unified server combining capabilities from all domain servers in one interface.

#### Tool Categories:
- **Database** (10 tools): All oci-db tools
- **Compute** (7 tools): All oci-compute tools prefixed with `compute_`
- **Network** (6 tools): All oci-network tools prefixed with `network_`
- **Security** (6 tools): All oci-security tools prefixed with `security_`
- **Inventory** (3 tools): ShowOCI and discovery tools
- **Block Storage** (2 tools): Volume management
- **Load Balancer** (2 tools): LB management
- **Log Analytics** (5 tools): Logan query tools prefixed with `logan_`
- **Skills** (24 tools): All skill-based tools for analysis and reporting

---

### 14. finopsai (12 tools)

**Purpose**: Advanced FinOps intelligence for cost optimization.

#### Tools:
- `templates` - Get analysis templates
- `cost_by_compartment_daily` - Daily compartment costs
- `service_cost_drilldown` - Service-level breakdown
- `cost_by_tag_key_value` - Tag-based cost analysis
- `monthly_trend_forecast` - Cost forecasting
- `focus_etl_healthcheck` - ETL health check
- `budget_status_and_actions` - Budget monitoring
- `schedule_report_create_or_list` - Report scheduling
- `object_storage_costs_and_tiering` - Storage optimization
- `top_cost_spikes_explain` - Anomaly detection
- `per_compartment_unit_cost` - Unit cost analysis
- `forecast_vs_universal_credits` - Credit management

---

### 15. opsi (39 tools)

**Purpose**: Operations Insights - database performance analysis and optimization.

#### Tools:
- **Profile Management**: `ping`, `whoami`, `list_oci_profiles`, `get_profile_info`
- **Cache Management**: `build_database_cache`, `get_cached_statistics`, `list_cached_compartments`, `refresh_cache_if_needed`, `refresh_all_caches`
- **Database Discovery**: `get_fleet_summary`, `search_databases`, `get_databases_by_compartment`
- **Operations Insights**: `list_database_insights`, `query_warehouse_standard`, `list_sql_texts`, `get_operations_insights_summary`, `summarize_database_insights`
- **SQLWatch**: `get_sqlwatch_status`, `enable_sqlwatch`, `disable_sqlwatch`, `get_sqlwatch_work_request`
- **Skills**: Database discovery, fleet summary, performance analysis, cost optimization

---

## Using the MCP Gateway

### Starting the Gateway

```bash
cd /Users/abirzu/dev/MCP/shared_test_infra
MCP_BASE_PATH=/Users/abirzu/dev/MCP python mcp_http_gateway.py
```

### Gateway Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Gateway health check |
| `GET /servers` | List all servers |
| `GET /servers/{name}/tools` | List tools for a server |
| `POST /servers/{name}/tools/{tool}` | Invoke a tool |
| `GET /telemetry/status` | OpenTelemetry status |

### Example API Calls

```bash
# List all servers
curl http://localhost:8080/servers | jq

# Get tools for oci-compute
curl http://localhost:8080/servers/oci-compute/tools | jq

# Call a tool
curl -X POST http://localhost:8080/servers/oci-cost/tools/cost_summary \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"days": 7}}'
```

---

## OpenTelemetry / OCI APM Integration

The gateway supports OpenTelemetry tracing to OCI APM:

```bash
# Enable OCI APM
export OCI_APM_ENDPOINT="https://your-apm.apm-agt.us-phoenix-1.oci.oraclecloud.com"
export OCI_APM_PRIVATE_KEY="your-private-key"

# Enable console tracing for debugging
export OTEL_CONSOLE_EXPORT=true
```

---

## Test Results Summary

```
Total Servers: 15
  OK: 15
  Error: 0
Total Tools Available: 273
```

All servers passed connectivity and tool listing tests as of December 17, 2025.
