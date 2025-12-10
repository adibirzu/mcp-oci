# MCP-OCI Skills Guide

This guide documents the skills layer for the MCP-OCI server, which provides composable, high-level operations following the [skillz pattern](https://github.com/intellectronica/skillz).

## Overview

The MCP-OCI skills layer transforms low-level OCI tools into intelligent, composable capabilities:

| Skill | Purpose | Key Methods |
|-------|---------|-------------|
| `CostAnalysisSkill` | Cost analysis, trending, optimization | `analyze_cost_trend`, `detect_anomalies`, `generate_optimization_report` |
| `InventoryAuditSkill` | Resource discovery, capacity planning | `run_full_discovery`, `generate_capacity_report`, `generate_audit_report` |
| `NetworkDiagnosticsSkill` | Network topology, security assessment | `analyze_topology`, `assess_security`, `generate_network_report` |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP-OCI Server                          │
├─────────────────────────────────────────────────────────────┤
│  Skills Layer                                               │
│  ├── CostAnalysisSkill                                      │
│  ├── InventoryAuditSkill                                    │
│  └── NetworkDiagnosticsSkill                                │
├─────────────────────────────────────────────────────────────┤
│  Adapters                                                   │
│  ├── CostClientAdapter                                      │
│  ├── InventoryClientAdapter                                 │
│  └── NetworkClientAdapter                                   │
├─────────────────────────────────────────────────────────────┤
│  Underlying Server Modules                                  │
│  ├── cost/server.py (FinOpsAI integration)                  │
│  ├── inventory/server.py (ShowOCI, capacity reports)        │
│  └── network/server.py (VCN, subnet management)             │
└─────────────────────────────────────────────────────────────┘
```

## Skills Reference

### CostAnalysisSkill

Provides comprehensive cost analysis, trend detection, and optimization recommendations.

#### Methods

##### `analyze_cost_trend(tenancy_ocid, months_back=6, budget_ocid=None)`

Analyze cost trends over time with forecasting.

```python
from mcp_servers.skills import CostAnalysisSkill

skill = CostAnalysisSkill()
result = skill.analyze_cost_trend(
    tenancy_ocid="ocid1.tenancy.oc1..xxx",
    months_back=6,
    budget_ocid="ocid1.budget.oc1..xxx"  # optional
)

# Returns:
# {
#   "analysis_type": "cost_trend",
#   "trend": {"direction": "increasing", "change_percent": 15.2},
#   "forecast": {"next_month": 5420.50, "currency": "USD"},
#   "recommendations": [...]
# }
```

##### `detect_anomalies(tenancy_ocid, time_start, time_end, threshold=2.0, top_n=10)`

Detect cost anomalies and spikes with explanations.

```python
result = skill.detect_anomalies(
    tenancy_ocid="ocid1.tenancy.oc1..xxx",
    time_start="2025-01-01",
    time_end="2025-01-31",
    threshold=2.0,
    top_n=10
)

# Returns anomalies with severity classification and explanations
```

##### `get_service_breakdown(tenancy_ocid, time_start, time_end, top_n=10)`

Get detailed service cost breakdown with optimization potential.

##### `generate_optimization_report(tenancy_ocid, days_back=30)`

Generate comprehensive cost optimization report combining all analyses.

---

### InventoryAuditSkill

Provides comprehensive resource discovery, capacity planning, and infrastructure auditing.

#### Methods

##### `run_full_discovery(compartment_id=None, region=None, limit_per_type=50)`

Run full infrastructure discovery with health assessment.

```python
from mcp_servers.skills import InventoryAuditSkill

skill = InventoryAuditSkill()
result = skill.run_full_discovery(
    compartment_id="ocid1.compartment.oc1..xxx",
    region="us-phoenix-1"
)

# Returns:
# {
#   "discovery_type": "full_infrastructure",
#   "resource_summary": [...],
#   "total_resources": 150,
#   "health_assessment": {...},
#   "tagging_compliance": {...}
# }
```

##### `generate_capacity_report(compartment_id=None, region=None, include_metrics=True)`

Generate compute capacity planning report with utilization analysis.

```python
result = skill.generate_capacity_report(
    compartment_id="ocid1.compartment.oc1..xxx"
)

# Returns:
# {
#   "report_type": "capacity_planning",
#   "utilization_analysis": {...},
#   "shape_analysis": {...},
#   "availability_analysis": {...},
#   "overall_assessment": {"score": 85.0, "status": "good"}
# }
```

##### `detect_changes(profile=None, regions=None, compartments=None)`

Detect infrastructure changes using ShowOCI diff mode.

##### `generate_audit_report(compartment_id=None, region=None)`

Generate comprehensive infrastructure audit report.

---

### NetworkDiagnosticsSkill

Provides network topology analysis, security assessment, and connectivity diagnostics.

#### Methods

##### `analyze_topology(compartment_id=None)`

Analyze network topology including VCNs, subnets, and relationships.

```python
from mcp_servers.skills import NetworkDiagnosticsSkill

skill = NetworkDiagnosticsSkill()
result = skill.analyze_topology(
    compartment_id="ocid1.compartment.oc1..xxx"
)

# Returns:
# {
#   "analysis_type": "network_topology",
#   "topology": {
#     "vcns": [...],
#     "total_vcns": 5,
#     "total_subnets": 15,
#     "cidr_analysis": [...]
#   },
#   "insights": [...],
#   "recommendations": [...]
# }
```

##### `assess_security(compartment_id=None)`

Assess network security posture with scoring.

```python
result = skill.assess_security(
    compartment_id="ocid1.compartment.oc1..xxx"
)

# Returns:
# {
#   "security_score": 85,
#   "status": "good",
#   "findings": [...],
#   "public_exposure_summary": [...]
# }
```

##### `diagnose_connectivity(compartment_id=None)`

Diagnose network connectivity configuration.

##### `generate_network_report(compartment_id=None)`

Generate comprehensive network diagnostic report.

---

## Tool Tiering

Skills internally use tools organized by tier:

### Tier 1: Instant (Management API)
- `healthcheck()` - Server health check
- `doctor()` - Configuration summary
- `get_tenancy_info()` - Tenancy details from cache
- `get_cache_stats()` - Cache statistics
- `list_vcns()` - VCN listing (cached)
- `list_subnets()` - Subnet listing (cached)

### Tier 2: API (1-30s response)
- `cost_by_compartment_daily()` - Usage API query
- `service_cost_drilldown()` - Service breakdown
- `monthly_trend_forecast()` - Trend analysis
- `top_cost_spikes_explain()` - Anomaly detection
- `run_showoci()` - ShowOCI inventory
- `generate_compute_capacity_report()` - Capacity analysis
- `summarize_public_endpoints()` - Security summary

### Tier 3: Mutating (Requires ALLOW_MUTATIONS)
- `create_vcn()` - Create VCN
- `create_subnet()` - Create subnet
- `create_vcn_with_subnets()` - Orchestrated network creation
- `refresh_local_cache()` - Cache refresh

## Usage Patterns

### Pattern 1: Quick Health Check

```python
from mcp_servers.skills import InventoryAuditSkill

skill = InventoryAuditSkill()

# Check tenancy health
tenancy = skill.client.get_tenancy_info()
cache = skill.client.get_cache_stats()

print(f"Tenancy: {tenancy['tenancy']['name']}")
print(f"Cache age: {cache['age_minutes']} minutes")
```

### Pattern 2: Cost Investigation

```python
from mcp_servers.skills import CostAnalysisSkill

skill = CostAnalysisSkill()

# Step 1: Check trend
trend = skill.analyze_cost_trend(tenancy_ocid, months_back=3)
print(f"Trend: {trend['trend']['direction']}")

# Step 2: If increasing, find anomalies
if trend['trend']['direction'] == 'increasing':
    anomalies = skill.detect_anomalies(
        tenancy_ocid,
        time_start="2025-01-01",
        time_end="2025-01-31"
    )
    print(f"Anomalies: {anomalies['total_anomalies']}")

# Step 3: Get service breakdown
breakdown = skill.get_service_breakdown(
    tenancy_ocid,
    time_start="2025-01-01",
    time_end="2025-01-31"
)
print(f"Top service: {breakdown['services'][0]['service']}")
```

### Pattern 3: Security Audit

```python
from mcp_servers.skills import NetworkDiagnosticsSkill, InventoryAuditSkill

network = NetworkDiagnosticsSkill()
inventory = InventoryAuditSkill()

# Network security
security = network.assess_security(compartment_id)
print(f"Security score: {security['security_score']}/100")

# Tagging compliance (from inventory)
discovery = inventory.run_full_discovery(compartment_id)
compliance = discovery['tagging_compliance']
print(f"Tagging compliance: {compliance['compliance_rate']}%")
```

### Pattern 4: Full Infrastructure Report

```python
from mcp_servers.skills import (
    CostAnalysisSkill,
    InventoryAuditSkill,
    NetworkDiagnosticsSkill
)

# Generate all reports
cost_report = CostAnalysisSkill().generate_optimization_report(tenancy_ocid)
inventory_report = InventoryAuditSkill().generate_audit_report(compartment_id)
network_report = NetworkDiagnosticsSkill().generate_network_report(compartment_id)

# Combine into executive summary
print(f"Cost: {cost_report['executive_summary']}")
print(f"Inventory: {inventory_report['executive_summary']}")
print(f"Network: {network_report['executive_summary']}")
```

## Recommendations Format

All skills generate recommendations in a consistent format:

```python
{
    "priority": "critical" | "high" | "medium" | "low",
    "category": "string",  # e.g., "cost_control", "security", "optimization"
    "description": "Human-readable description",
    "action": "Specific action to take"
}
```

Recommendations are automatically prioritized in report outputs.

## Error Handling

Skills return error responses in a consistent format:

```python
{
    "error": "Error description"
}
```

Check for error keys before processing results:

```python
result = skill.analyze_cost_trend(tenancy_ocid)
if "error" in result:
    print(f"Analysis failed: {result['error']}")
else:
    print(f"Trend: {result['trend']['direction']}")
```

## Best Practices

1. **Start with cached data** - Use Tier 1 tools for quick checks before API calls
2. **Scope appropriately** - Always provide compartment_id when possible
3. **Use reports for comprehensive analysis** - `generate_*_report()` methods aggregate multiple analyses
4. **Check recommendations** - Every analysis includes actionable recommendations
5. **Handle errors gracefully** - Always check for error responses

## Integration with MCP Client

The skills are exposed as MCP tools through the main.py server:

```python
# MCP tools for skills
skill_analyze_cost_trend(tenancy_ocid, months_back, budget_ocid)
skill_detect_cost_anomalies(tenancy_ocid, time_start, time_end, threshold, top_n)
skill_generate_cost_optimization_report(tenancy_ocid, days_back)
skill_run_infrastructure_discovery(compartment_id, region, limit_per_type)
skill_generate_capacity_report(compartment_id, region, include_metrics)
skill_generate_infrastructure_audit(compartment_id, region)
skill_analyze_network_topology(compartment_id)
skill_assess_network_security(compartment_id)
skill_generate_network_report(compartment_id)
```

These tools are discoverable via the `server://manifest` resource.
