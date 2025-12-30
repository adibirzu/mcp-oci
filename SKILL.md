---
name: oci-mcp
version: 2.0.0
description: Oracle Cloud Infrastructure MCP server providing comprehensive cloud management capabilities through the Model Context Protocol.
transport: stdio
---

# OCI MCP Server Skill

## Overview
This skill provides AI agents with comprehensive Oracle Cloud Infrastructure management capabilities through the Model Context Protocol. It follows Anthropic's best practices for code execution with MCP, featuring progressive disclosure, context efficiency, and high-level workflow skills.

## Quick Start

### 1. Discover Available Domains
```
oci_list_domains()
```

### 2. Search for Tools
```
oci_search_tools(query="cost analysis", detail_level="summary")
```

### 3. Get Server Health
```
oci_ping()
```

### 4. Execute Tool
```python
list_instances({
    "compartment_id": "ocid1.compartment...",
    "lifecycle_state": "RUNNING",
    "limit": 20,
    "format": "markdown"
})
```

## Available Domains

| Domain | Tools | Description |
|--------|-------|-------------|
| compute | 5 | Instance management, shapes, and metrics |
| cost | 5 | Cost analysis, budgets, FinOps |
| database | 5 | Autonomous DB, DB Systems, MySQL |
| network | 5 | VCN, Subnet, and Security List management |
| security | 6 | IAM, Cloud Guard, and policy management |
| observability | 2 | Logging Analytics and monitoring |
| skills | 1 | High-level workflow skills |
| discovery | 4 | Tool discovery and server info |

## Tool Tiers

### Tier 1 - Instant (<100ms)
- `oci_ping` - Health check
- `oci_list_domains` - List available domains
- `oci_search_tools` - Search for tools

### Tier 2 - API (100ms-1s)
- `list_instances` - List compute instances
- `get_instance_metrics` - Get performance metrics
- `get_logs` - Query logs
- `oci_network_list_vcns` - List Virtual Cloud Networks
- `oci_network_list_subnets` - List subnets
- `oci_security_list_users` - List IAM users
- `oci_security_list_policies` - List IAM policies

### Tier 3 - Heavy (1s-30s)
- `oci_network_analyze_security` - Analyze network security
- `oci_security_audit` - Comprehensive security audit

### Tier 4 - Admin (Write Operations)
- `start_instance` - Start a stopped instance
- `stop_instance` - Stop a running instance
- `restart_instance` - Restart an instance

## Authentication

The server supports multiple authentication methods:

1. **OCI Config File** (default): Uses `~/.oci/config`
2. **Instance Principal**: For OCI compute instances
3. **Resource Principal**: For OCI Functions

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `OCI_CONFIG_FILE` | No | Path to OCI config file |
| `OCI_PROFILE` | No | Profile name (default: DEFAULT) |
| `OCI_REGION` | No | Region override |
| `COMPARTMENT_OCID` | Yes | Default compartment |
| `ALLOW_MUTATIONS` | No | Enable write operations |

## Response Formats

All data-returning tools support format selection:

- **markdown** (default): Human-readable, concise output
- **json**: Machine-readable, complete data

```python
# Human-readable output
list_instances(format="markdown")

# Machine-readable output
list_instances(format="json")
```

## Skills (Workflow Operations)

Skills are high-level operations that combine multiple tools:

### troubleshoot_instance
Comprehensive instance troubleshooting that:
1. Checks instance state
2. Fetches recent metrics
3. Analyzes health indicators
4. Provides recommendations

## Best Practices

1. **Use Discovery First**: Always start with `oci_list_domains()` or `oci_search_tools()` to find relevant tools
2. **Prefer Markdown Format**: Use `format="markdown"` for exploratory queries to save context
3. **Use JSON for Processing**: Use `format="json"` when you need to process the data programmatically
4. **Check Pagination**: List operations may have more results - check `has_more` flag
5. **Verify Before Mutations**: Use read operations to verify state before write operations

## Error Handling

All tools return structured errors with:
- Error message explaining what went wrong
- Suggestion for how to resolve the issue

Example error:
```
Error: Resource not found. Verify the OCID is correct and the resource exists in the specified region.
```

## Security Considerations

- Write operations (start/stop/restart) require `ALLOW_MUTATIONS=true`
- All credentials are read from environment variables or OCI config
- No secrets are ever hardcoded or logged
