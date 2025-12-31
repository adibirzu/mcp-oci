---
name: oci-mcp
version: 2.3.0
description: Oracle Cloud Infrastructure MCP server providing comprehensive cloud management capabilities through the Model Context Protocol.
transport: stdio
tools: 44
---

# OCI MCP Server Skill

## Overview

This skill provides AI agents with comprehensive Oracle Cloud Infrastructure management capabilities through the Model Context Protocol. It follows Anthropic's best practices for code execution with MCP, featuring progressive disclosure, context efficiency, and high-level workflow skills.

## Quick Start

### 1. Discover Available Domains
```python
oci_list_domains()
```
Returns: compute, network, database, security, cost, observability

### 2. Search for Tools
```python
oci_search_tools(query="instances", detail_level="summary")
```

### 3. Get Server Health
```python
oci_ping()
```

### 4. Execute Tool
```python
oci_compute_list_instances({
    "compartment_id": "ocid1.compartment...",
    "lifecycle_state": "RUNNING",
    "limit": 20,
    "response_format": "markdown"
})
```

## Tool Naming Convention

All tools follow the pattern: `oci_{domain}_{action}_{resource}`

Examples:
- `oci_compute_list_instances` - List compute instances
- `oci_network_get_vcn` - Get VCN details
- `oci_security_audit` - Run security audit

## Available Domains

| Domain | Tools | Description |
|--------|-------|-------------|
| discovery | 4 | Tool discovery, server info, cache stats |
| compute | 5 | Instance management and metrics |
| network | 5 | VCN, Subnet, Security List management |
| database | 5 | Autonomous DB, DB Systems, MySQL |
| security | 6 | IAM, Cloud Guard, policy management |
| cost | 5 | Cost analysis, budgets, FinOps |
| observability | 6 | Metrics, Logs, Alarms |
| skills | 1 | High-level workflow skills |

## Complete Tool Inventory

### Discovery (Tier 1 - Instant, <100ms)

| Tool | Description |
|------|-------------|
| `oci_ping` | Server health check |
| `oci_list_domains` | List available capability domains |
| `oci_search_tools` | Search for tools by keyword |
| `oci_get_cache_stats` | Get cache performance statistics |

### Compute (Tier 2-4)

| Tool | Tier | Description |
|------|------|-------------|
| `oci_compute_list_instances` | 2 | List compute instances with filtering |
| `oci_compute_get_instance` | 2 | Get instance details with metrics |
| `oci_compute_start_instance` | 4 | Start a stopped instance |
| `oci_compute_stop_instance` | 4 | Stop a running instance |
| `oci_compute_restart_instance` | 4 | Restart an instance |

### Network (Tier 2-3)

| Tool | Tier | Description |
|------|------|-------------|
| `oci_network_list_vcns` | 2 | List Virtual Cloud Networks |
| `oci_network_get_vcn` | 2 | Get VCN details |
| `oci_network_list_subnets` | 2 | List subnets in a VCN |
| `oci_network_list_security_lists` | 2 | List security lists |
| `oci_network_analyze_security` | 3 | Analyze security configuration |

### Database (Tier 2)

| Tool | Tier | Description |
|------|------|-------------|
| `oci_database_list_autonomous` | 2 | List Autonomous Databases |
| `oci_database_get_autonomous` | 2 | Get ADB details |
| `oci_database_list_db_systems` | 2 | List DB Systems |
| `oci_database_get_db_system` | 2 | Get DB System details |
| `oci_database_list_mysql` | 2 | List MySQL instances |

### Security (Tier 2-3)

| Tool | Tier | Description |
|------|------|-------------|
| `oci_security_list_users` | 2 | List IAM users |
| `oci_security_get_user` | 2 | Get user details |
| `oci_security_list_groups` | 2 | List IAM groups |
| `oci_security_list_policies` | 2 | List IAM policies |
| `oci_security_list_cloud_guard_problems` | 2 | List Cloud Guard problems |
| `oci_security_audit` | 3 | Comprehensive security audit |

### Cost (Tier 2-3)

| Tool | Tier | Description |
|------|------|-------------|
| `oci_cost_get_summary` | 2 | Get cost summary for period |
| `oci_cost_by_service` | 2 | Get cost by service |
| `oci_cost_by_compartment` | 2 | Get cost by compartment |
| `oci_cost_monthly_trend` | 2 | Month-over-month trends |
| `oci_cost_detect_anomalies` | 3 | Detect cost anomalies |

### Observability (Tier 2-3)

| Tool | Tier | Description |
|------|------|-------------|
| `oci_observability_get_instance_metrics` | 3 | Get instance metrics |
| `oci_observability_execute_log_query` | 3 | Execute Log Analytics query |
| `oci_observability_list_alarms` | 2 | List monitoring alarms |
| `oci_observability_get_alarm_history` | 2 | Get alarm history |
| `oci_observability_list_log_sources` | 2 | List log sources |
| `oci_observability_overview` | 3 | Observability overview |

### Skills (Tier 3)

| Tool | Tier | Description |
|------|------|-------------|
| `oci_skill_troubleshoot_instance` | 3 | Comprehensive instance troubleshooting |

### Tool Aliases (Backward Compatibility)

For agents using shorter tool names:

| Alias | Canonical Tool |
|-------|----------------|
| `list_instances` | `oci_compute_list_instances` |
| `start_instance` | `oci_compute_start_instance` |
| `stop_instance` | `oci_compute_stop_instance` |
| `restart_instance` | `oci_compute_restart_instance` |
| `get_instance_metrics` | `oci_observability_get_instance_metrics` |

## Tool Tiers

| Tier | Latency | Description | Risk |
|------|---------|-------------|------|
| 1 | <100ms | Cached/instant | None |
| 2 | 100ms-1s | Single API call | None |
| 3 | 1s-30s | Heavy analytics | Low |
| 4 | Variable | Mutations | Medium-High |

## Authentication

The server supports multiple authentication methods:

1. **OCI Config File** (default): Uses `~/.oci/config`
2. **Instance Principal**: For OCI compute instances
3. **Resource Principal**: For OCI Functions

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OCI_CONFIG_FILE` | No | `~/.oci/config` | Path to OCI config file |
| `OCI_CLI_PROFILE` | No | `DEFAULT` | Profile name |
| `OCI_REGION` | No | From config | Region override |
| `COMPARTMENT_OCID` | Yes | - | Default compartment |
| `ALLOW_MUTATIONS` | No | `false` | Enable write operations |
| `OCI_MCP_TRANSPORT` | No | `stdio` | Transport mode |
| `OCI_MCP_LOG_LEVEL` | No | `INFO` | Logging level |

## Response Formats

All data-returning tools support format selection:

### Markdown (default)
Human-readable, concise output optimized for LLM context:
```python
oci_compute_list_instances(response_format="markdown")
```

### JSON
Machine-readable, complete data for programmatic processing:
```python
oci_compute_list_instances(response_format="json")
```

## Pagination

All list operations support pagination:
```python
oci_compute_list_instances({
    "compartment_id": "ocid1.compartment...",
    "limit": 20,
    "offset": 0
})
```

Check the `has_more` flag in the response to determine if more results exist.

## Best Practices

1. **Discovery First**: Start with `oci_list_domains()` or `oci_search_tools()` to find relevant tools
2. **Prefer Markdown**: Use `response_format="markdown"` for exploratory queries to save context
3. **Use JSON for Processing**: Use `response_format="json"` when processing data programmatically
4. **Check Pagination**: List operations may have more results - check `has_more` flag
5. **Verify Before Mutations**: Use read operations to verify state before write operations
6. **Handle Errors**: All tools return structured errors with suggestions

## Error Handling

All tools return structured errors with:
- Error category (authentication, authorization, not_found, etc.)
- Error message explaining what went wrong
- Suggestion for how to resolve the issue

Example error:
```
## Error
**Category:** not_found
**Message:** Instance not found
**Suggestion:** Verify the OCID is correct and the resource exists in the specified region.
```

## Security Considerations

- Write operations (start/stop/restart) require `ALLOW_MUTATIONS=true`
- All credentials are read from environment variables or OCI config
- No secrets are ever hardcoded or logged
- Request IDs are tracked for debugging

## Caching

The server includes tiered caching optimized for OCI data patterns:

| Cache Tier | TTL | Use Case |
|------------|-----|----------|
| `static` | 1 hour | Shapes, regions, services |
| `config` | 5 min | Compartments, VCNs |
| `operational` | 1 min | Instance status, metrics |
| `metrics` | 30 sec | Real-time monitoring |

Use `oci_get_cache_stats` to monitor cache performance.

## Skills Framework

Skills are high-level workflows that combine multiple tools:

### Using Skills

```python
oci_skill_troubleshoot_instance({
    "instance_id": "ocid1.instance...",
    "response_format": "markdown"
})
```

### Skills vs Tools

| Aspect | Tools | Skills |
|--------|-------|--------|
| Scope | Single operation | Multi-step workflow |
| Logic | Direct API call | Expert knowledge encoded |
| Output | Raw data | Analysis + recommendations |
| Duration | <1s typically | 1-30s |

### Creating New Skills

See the `skills/` directory for examples. Key patterns:
1. Use `SkillExecutor` for progress tracking
2. Call tools via `executor.call_tool()`
3. Use `executor.analyze()` for LLM-powered analysis
4. Return formatted results with recommendations

### Skills Framework Components

| Component | Description |
|-----------|-------------|
| `SkillExecutor` | Coordinates tool calls with timing and progress |
| `AgentContext` | Carries state between skill steps |
| `SamplingClient` | Enables LLM analysis during skill execution |
| `SkillProgress` | Tracks step completion percentages |

## Agent Context

For multi-step skills that need to maintain state:

```python
from mcp_server_oci.skills import AgentContext

context = AgentContext(skill_name="troubleshoot")
context.add_finding("cpu_high", {"value": 95, "threshold": 80})
context.add_recommendation("Consider scaling up the instance")
```

## Inter-Agent Communication

For skills that need to share findings across agent sessions:

```python
from mcp_server_oci.core import share_finding, get_shared_findings

# Share a finding
await share_finding(
    agent_id="troubleshooter",
    category="performance",
    severity="warning",
    message="High CPU on instance xyz"
)

# Retrieve shared findings
findings = await get_shared_findings(category="performance")
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.3.0 | 2025-12-31 | Skills framework, caching, shared memory, code quality fixes |
| 2.2.0 | 2025-12-30 | Tool aliases, observability enhancements |
| 2.0.0 | 2025-12-28 | FastMCP migration, progressive disclosure |
