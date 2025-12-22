# Individual MCP Server Documentation

This document provides detailed information about each MCP server, including available tools, configuration options, and usage examples.

## Table of Contents

1. [Compute Server](#compute-server)
2. [Cost Server](#cost-server)
3. [Security Server](#security-server)
4. [Network Server](#network-server)
5. [Database Server](#database-server)
6. [Block Storage Server](#blockstorage-server)
7. [Observability Server](#observability-server)
8. [Inventory Server](#inventory-server)
9. [Load Balancer Server](#loadbalancer-server)
10. [Agents Server](#agents-server)

---

## Compute Server

**Module:** `mcp_servers.compute.server`
**Default Port:** 8001
**Purpose:** Virtual machine and container instance management

### Available Tools

- `list_instances` - List compute instances with filtering
- `get_instance_details` - Get detailed instance information
- `start_instance` - Start a stopped instance
- `stop_instance` - Stop a running instance
- `restart_instance` - Restart an instance
- `terminate_instance` - Terminate an instance (destructive)
- `create_instance` - Create new compute instances
- `resize_instance` - Change instance shape/size
- `get_instance_console_connection` - Get console access
- `list_instance_configurations` - List saved configurations

### Configuration

```bash
# Required
export OCI_REGION=us-ashburn-1
export COMPARTMENT_OCID=[Link to Secure Variable: OCI_COMPARTMENT_OCID]

# Optional
export ALLOW_MUTATIONS=true  # Enable write operations
export METRICS_PORT=8001     # Prometheus metrics port
export MCP_CACHE_TTL_COMPUTE=3600  # Cache duration in seconds
```

### Usage Examples

```python
# List all instances in compartment
instances = list_instances(compartment_id="[Link to Secure Variable: OCI_COMPARTMENT_OCID]")

# Get specific instance details
details = get_instance_details(instance_id="[Link to Secure Variable: OCI_INSTANCE_OCID]")

# Start instance with confirmation
start_instance(instance_id="[Link to Secure Variable: OCI_INSTANCE_OCID]", confirm=True)
```

---

## Cost Server

**Module:** `mcp_servers.cost.server`
**Default Port:** 8005
**Purpose:** Financial operations and cost optimization

### Available Tools

- `service_cost_drilldown` - Analyze costs by service and compartment
- `cost_by_compartment_daily` - Daily cost breakdown by compartment
- `cost_by_tag_key_value` - Cost analysis by resource tags
- `list_tag_defaults` - Tagging rules (tag defaults)
- `cost_by_resource` - Cost by resource ID/name
- `cost_by_database` - Cost by database resources
- `cost_by_pdb` - Cost by PDB name (best-effort)
- `monthly_trend_forecast` - Cost trends and forecasting
- `object_storage_costs_and_tiering` - Storage cost optimization
- `top_cost_spikes_explain` - Identify and explain cost anomalies
- `per_compartment_unit_cost` - Unit economics analysis
- `forecast_vs_universal_credits` - Credit utilization forecasting
- `budget_status_and_actions` - Budget monitoring and alerts

### Configuration

```bash
# Required
export TENANCY_OCID=[Link to Secure Variable: OCI_TENANCY_OCID]
export OCI_REGION=us-ashburn-1

# Optional
export FINOPSAI_CACHE_TTL_SECONDS=600
export OCI_BILLING_NAMESPACE=oci_billing
export METRICS_PORT=8005
```

### Usage Examples

```python
# Get service cost breakdown
costs = service_cost_drilldown(
    tenancy_ocid="[Link to Secure Variable: OCI_TENANCY_OCID]",
    time_start="2024-01-01",
    time_end="2024-01-31",
    top_n=10
)

# Analyze cost by tags
tag_costs = cost_by_tag_key_value(
    tenancy_ocid="[Link to Secure Variable: OCI_TENANCY_OCID]",
    time_start="2024-01-01",
    time_end="2024-01-31",
    defined_tag_ns="FinOps",
    defined_tag_key="CostCenter",
    defined_tag_value="Engineering"
)
```

---

## Security Server

**Module:** `mcp_servers.security.server`
**Default Port:** 8004
**Purpose:** Security scanning and compliance management

### Available Tools

- `scan_compute_vulnerabilities` - Scan instances for vulnerabilities
- `analyze_network_security` - Network security assessment
- `check_iam_policies` - IAM policy analysis
- `compliance_scan` - Compliance framework checking
- `security_baseline_check` - Security baseline validation
- `threat_detection_analysis` - Threat detection and analysis
- `encrypt_volume` - Encrypt block volumes
- `rotate_keys` - Key rotation management
- `audit_trail_analysis` - Audit log analysis

### Configuration

```bash
# Required
export OCI_REGION=us-ashburn-1
export COMPARTMENT_OCID=[Link to Secure Variable: OCI_COMPARTMENT_OCID]

# Optional
export SECURITY_SCAN_ENABLED=true
export VULNERABILITY_DB_PATH=/path/to/vuln-db
export COMPLIANCE_FRAMEWORKS=PCI,SOX,GDPR
export METRICS_PORT=8004
```

### Usage Examples

```python
# Scan compute instances for vulnerabilities
scan_results = scan_compute_vulnerabilities(
    compartment_id="[Link to Secure Variable: OCI_COMPARTMENT_OCID]",
    severity_filter="HIGH,CRITICAL"
)

# Check compliance against framework
compliance = compliance_scan(
    compartment_id="[Link to Secure Variable: OCI_COMPARTMENT_OCID]",
    framework="PCI"
)
```

---

## Network Server

**Module:** `mcp_servers.network.server`
**Default Port:** 8006
**Purpose:** Networking and connectivity management

### Available Tools

- `list_vcns` - List Virtual Cloud Networks
- `create_vcn` - Create new VCN
- `list_subnets` - List subnets in VCN
- `create_subnet` - Create new subnet
- `list_security_lists` - List network security lists
- `update_security_list` - Update security list rules
- `list_route_tables` - List route tables
- `create_internet_gateway` - Create internet gateway
- `create_nat_gateway` - Create NAT gateway
- `test_connectivity` - Test network connectivity

### Configuration

```bash
# Required
export OCI_REGION=us-ashburn-1
export COMPARTMENT_OCID=[Link to Secure Variable: OCI_COMPARTMENT_OCID]

# Optional
export ALLOW_MUTATIONS=true
export MCP_CACHE_TTL_NETWORKING=1800
export METRICS_PORT=8006
```

---

## Database Server

**Module:** `mcp_servers.db.server`
**Default Port:** 8002
**Purpose:** Database service management

### Available Tools

- `list_autonomous_databases` - List Autonomous Databases
- `create_autonomous_database` - Create new ADB
- `start_autonomous_database` - Start stopped ADB
- `stop_autonomous_database` - Stop running ADB
- `scale_autonomous_database` - Scale ADB resources
- `list_db_systems` - List DB Systems
- `create_db_backup` - Create database backup
- `restore_db_backup` - Restore from backup
- `get_db_performance_metrics` - Get performance metrics

### Configuration

```bash
# Required
export OCI_REGION=us-ashburn-1
export COMPARTMENT_OCID=[Link to Secure Variable: OCI_COMPARTMENT_OCID]

# Optional for wallet-based connections
export ORACLE_DB_USER=ADMIN
export ORACLE_DB_PASSWORD=SecurePassword123!
export ORACLE_DB_WALLET_ZIP=/path/to/wallet.zip
export METRICS_PORT=8002
```

---

## Block Storage Server

**Module:** `mcp_servers.blockstorage.server`
**Default Port:** 8007
**Purpose:** Block volume management

### Available Tools

- `list_volumes` - List block volumes
- `create_volume` - Create new volume
- `attach_volume` - Attach volume to instance
- `detach_volume` - Detach volume from instance
- `create_volume_backup` - Create volume backup
- `restore_volume_backup` - Restore from backup
- `resize_volume` - Resize volume
- `clone_volume` - Clone existing volume
- `list_volume_backups` - List volume backups

### Configuration

```bash
# Required
export OCI_REGION=us-ashburn-1
export COMPARTMENT_OCID=[Link to Secure Variable: OCI_COMPARTMENT_OCID]

# Optional
export ALLOW_MUTATIONS=true
export METRICS_PORT=8007
```

---

## Observability Server

**Module:** `mcp_servers.observability.server`
**Default Port:** 8003
**Purpose:** Monitoring and observability management

### Available Tools

- `create_alarm` - Create monitoring alarms
- `list_metrics` - List available metrics
- `get_metric_data` - Get metric time series data
- `create_log_group` - Create log group
- `search_logs` - Search log entries
- `create_apm_domain` - Create APM domain
- `get_trace_details` - Get distributed trace details
- `create_dashboard` - Create monitoring dashboard
- `export_logs` - Export logs to object storage

### Configuration

```bash
# Required
export OCI_REGION=us-ashburn-1
export COMPARTMENT_OCID=[Link to Secure Variable: OCI_COMPARTMENT_OCID]

# Optional
export OCI_MONITORING_NAMESPACE=custom_metrics
export METRICS_PORT=8003
```

---

## Inventory Server

**Module:** `mcp_servers.inventory.server`
**Default Port:** 8009
**Purpose:** Asset discovery and inventory management

### Available Tools

- `discover_resources` - Discover all resources in compartment
- `list_resource_types` - List available resource types
- `get_resource_details` - Get detailed resource information
- `tag_resources` - Apply tags to resources
- `generate_inventory_report` - Generate comprehensive inventory
- `check_resource_compliance` - Check resource compliance
- `find_unused_resources` - Find unused/idle resources
- `cost_by_resource_type` - Cost analysis by resource type

### Configuration

```bash
# Required
export OCI_REGION=us-ashburn-1
export COMPARTMENT_OCID=[Link to Secure Variable: OCI_COMPARTMENT_OCID]

# Optional
export INCLUDE_CHILD_COMPARTMENTS=true
export METRICS_PORT=8009
```

---

## Load Balancer Server

**Module:** `mcp_servers.loadbalancer.server`
**Default Port:** 8008
**Purpose:** Load balancer management

### Available Tools

- `list_load_balancers` - List load balancers
- `create_load_balancer` - Create new load balancer
- `update_load_balancer` - Update load balancer configuration
- `create_backend_set` - Create backend set
- `add_backend` - Add backend server
- `create_listener` - Create listener
- `manage_certificates` - Manage SSL certificates
- `get_health_status` - Get health check status
- `update_health_checker` - Update health check configuration

### Configuration

```bash
# Required
export OCI_REGION=us-ashburn-1
export COMPARTMENT_OCID=[Link to Secure Variable: OCI_COMPARTMENT_OCID]

# Optional
export ALLOW_MUTATIONS=true
export METRICS_PORT=8008
```

---

## Agents Server

**Module:** `mcp_servers.agents.server`
**Default Port:** 8011
**Purpose:** OCI Generative AI agents integration

### Available Tools

- `list_agents` - List available AI agents
- `create_agent` - Create new AI agent
- `chat_with_agent` - Chat with AI agent
- `get_agent_capabilities` - Get agent capabilities
- `create_knowledge_base` - Create agent knowledge base
- `upload_documents` - Upload documents to knowledge base
- `configure_agent_tools` - Configure agent tools
- `get_conversation_history` - Get chat history
- `agent_performance_metrics` - Get agent performance metrics

### Configuration

```bash
# Required
export OCI_REGION=us-ashburn-1
export COMPARTMENT_OCID=[Link to Secure Variable: OCI_COMPARTMENT_OCID]

# Optional
export GAI_AGENT_ENDPOINT=http://localhost:8088/agents/chat
export GAI_AGENT_API_KEY=[Link to Secure Variable: GAI_AGENT_API_KEY]
export METRICS_PORT=8011
```

---

## Common Configuration Patterns

### Authentication

All servers support these authentication methods:

1. **OCI CLI Config** (Default)
   ```bash
   export OCI_PROFILE=DEFAULT
   ```

2. **Resource Principal** (Auto-detected on OCI compute)
   ```bash
   # No configuration needed - auto-detected
   ```

3. **Instance Principal** (For OCI compute instances)
   ```bash
   export OCI_AUTH_TYPE=instance_principal
   ```

### Observability Integration

All servers automatically expose metrics:

```bash
# Server-specific metrics
curl http://localhost:800X/metrics

# Common metrics available:
# - mcp_tool_calls_total
# - mcp_tool_duration_seconds
# - http_requests_total
# - http_request_duration_seconds
```

### Error Handling

All servers use consistent error handling:

- Operations return structured error responses
- Destructive operations require explicit confirmation
- All operations are logged for audit purposes
- Rate limiting and retry logic built-in

### Cache Configuration

Servers support intelligent caching:

```bash
# Per-server cache TTL
export MCP_CACHE_TTL_COMPUTE=3600      # Compute operations
export MCP_CACHE_TTL_NETWORKING=1800   # Network operations
export MCP_CACHE_TTL_FUNCTIONS=1800    # Function operations
export MCP_CACHE_TTL_STREAMING=1200    # Streaming operations

# Global cache TTL
export MCP_CACHE_TTL=3600
```

This caching reduces API calls, improves performance, and minimizes costs.
