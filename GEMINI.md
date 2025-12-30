# Project Context: mcp-oci-new

## Overview
This is a **modernized OCI MCP Server** implementing the OCI MCP Server Standard v2.1, featuring:
- **FastMCP** server framework
- **Progressive disclosure** through tool discovery
- **Pydantic v2** input models with validation
- **Dual response formats** (markdown/JSON)
- **Domain-organized tools** with SKILL.md documentation

## Directory Structure
```
src/mcp_server_oci/
├── server.py              # FastMCP entrypoint and tool registration
├── config.py              # Configuration management (Pydantic Settings)
├── core/                  # Shared infrastructure
│   ├── __init__.py        # Exports all core utilities
│   ├── client.py          # OCI SDK wrapper with auth methods
│   ├── errors.py          # Structured error handling (OCIError)
│   ├── formatters.py      # Response formatters (markdown/JSON)
│   ├── models.py          # Shared models (HealthStatus, etc.)
│   └── observability.py   # Logging and tracing setup
├── tools/                 # Domain-organized tools
│   ├── compute/           # ✅ Complete (5 tools)
│   │   ├── models.py      # Pydantic v2 input models
│   │   ├── tools.py       # Tool implementations
│   │   ├── formatters.py  # Domain-specific formatters
│   │   └── SKILL.md       # Agent guidance
│   ├── cost/              # ✅ Complete (5 tools)
│   │   └── ...
│   ├── database/          # ✅ Complete (5 tools)
│   │   └── ...
│   ├── network/           # ✅ Complete (5 tools)
│   │   └── ...
│   ├── security/          # ✅ Complete (6 tools)
│   │   └── ...
│   └── observability/     # ⚠️ Legacy (2 tools, needs refactor)
│       └── ...
└── skills/                # High-level workflow skills
    ├── troubleshoot.py    # troubleshoot_instance skill
    └── SKILL.md
```

## Implementation Status

### ✅ Complete
| Component | Description |
|-----------|-------------|
| Core Infrastructure | config, client, errors, formatters, models, observability |
| Discovery Tools | oci_ping, oci_list_domains, oci_search_tools |
| Server Manifest | server://manifest resource |
| Cost Domain | 5 tools (summary, by_service, by_compartment, monthly_trend, detect_anomalies) |
| Compute Domain | 5 tools (list, start, stop, restart, get_metrics) |
| Database Domain | 5 tools (list_autonomous, get, start, stop, list_dbsystems) |
| Network Domain | 5 tools (list_vcns, get_vcn, list_subnets, list_security_lists, analyze_security) |
| Security Domain | 6 tools (list_users, get_user, list_groups, list_policies, list_cloud_guard_problems, audit) |
| SKILL.md Files | Main + all domains |

### ⚠️ Partial
- **Observability**: Legacy implementation, needs Pydantic model refactor
- **Skills**: Only troubleshoot_instance implemented

### ❌ Not Started
- **Evaluation XMLs**: Testing framework
- **Unit Tests**: pytest coverage

## Usage

### Development
```bash
# Install dependencies
uv sync

# Run server (stdio mode)
uv run python -m mcp_server_oci

# Run server (HTTP mode)
OCI_MCP_TRANSPORT=streamable_http uv run python -m mcp_server_oci
```

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `OCI_CONFIG_FILE` | OCI config file path | ~/.oci/config |
| `OCI_PROFILE` | OCI config profile | DEFAULT |
| `OCI_REGION` | Target region | From config |
| `COMPARTMENT_OCID` | Default compartment | Required |
| `ALLOW_MUTATIONS` | Enable write operations | false |
| `OCI_MCP_TRANSPORT` | stdio or streamable_http | stdio |
| `OCI_MCP_PORT` | HTTP port | 8000 |

## Tool Inventory (28 tools)

### Discovery (Tier 1)
- `oci_ping` - Health check
- `oci_list_domains` - List capability areas
- `oci_search_tools` - Search for tools

### Cost Domain (Tier 2-3)
- `oci_cost_get_summary` - Cost summary for time window
- `oci_cost_by_service` - Top services by cost
- `oci_cost_by_compartment` - Cost breakdown by compartment
- `oci_cost_monthly_trend` - Monthly trends with forecast
- `oci_cost_detect_anomalies` - Cost spike detection

### Compute Domain (Tier 2-4)
- `oci_compute_list_instances` - List instances with filtering
- `oci_compute_start_instance` - Start instance
- `oci_compute_stop_instance` - Stop instance
- `oci_compute_restart_instance` - Restart instance
- `oci_compute_get_metrics` - Performance metrics

### Database Domain (Tier 2-4)
- `oci_database_list_autonomous` - List Autonomous DBs
- `oci_database_get_autonomous` - Get ADB details
- `oci_database_start_autonomous` - Start ADB
- `oci_database_stop_autonomous` - Stop ADB
- `oci_database_list_dbsystems` - List DB Systems

### Network Domain (Tier 2-3)
- `oci_network_list_vcns` - List VCNs
- `oci_network_get_vcn` - Get VCN details
- `oci_network_list_subnets` - List subnets
- `oci_network_list_security_lists` - List security lists
- `oci_network_analyze_security` - Security analysis

### Security Domain (Tier 2-3)
- `oci_security_list_users` - List IAM users
- `oci_security_get_user` - Get user details
- `oci_security_list_groups` - List IAM groups
- `oci_security_list_policies` - List IAM policies
- `oci_security_list_cloud_guard_problems` - Cloud Guard problems
- `oci_security_audit` - Comprehensive security audit

### Observability (Tier 2) - Legacy
- `get_instance_metrics` - Instance metrics
- `get_logs` - Log query

### Skills (Tier 3)
- `troubleshoot_instance` - Instance troubleshooting workflow

## Next Steps
1. Refactor Observability to new pattern (models.py, formatters.py, tools.py)
2. Add evaluation XMLs (10 questions per domain)
3. Add unit tests with pytest
4. Add more workflow skills (cost optimization, network troubleshooting)
