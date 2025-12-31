# OCI MCP Server Architecture

**Version:** 2.3.0
**Last Updated:** 2025-12-31
**Total Tools:** 44 (including aliases)

---

## 1. Overview

The OCI MCP Server provides AI agents with comprehensive Oracle Cloud Infrastructure management capabilities through the Model Context Protocol (MCP). It follows Anthropic's best practices for progressive disclosure, context efficiency, and high-level workflow skills.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AI Agent (Claude)                           │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │ MCP Protocol (stdio/SSE)
┌─────────────────────────────────────▼───────────────────────────────┐
│                         OCI MCP Server                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     Progressive Disclosure                   │    │
│  │   oci_ping │ oci_list_domains │ oci_search_tools            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Compute  │ │ Network  │ │ Database │ │ Security │ │   Cost   │  │
│  │  Tools   │ │  Tools   │ │  Tools   │ │  Tools   │ │  Tools   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│       └────────────┴────────────┴────────────┴────────────┘        │
│                              │                                      │
│  ┌───────────────────────────▼─────────────────────────────────┐   │
│  │                    OCI Client Manager                        │   │
│  │   ComputeClient│NetworkClient│IdentityClient│UsageApiClient │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                      │
                    OCI SDK (REST API)
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Oracle Cloud Infrastructure                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure

```
src/mcp_server_oci/
├── __init__.py
├── server.py                 # FastMCP server entry point + tool aliases
├── config.py                 # Pydantic settings configuration
├── auth.py                   # OCI authentication handling
│
├── core/                     # Core infrastructure
│   ├── __init__.py           # Unified exports for all core modules
│   ├── client.py             # OCI SDK client manager
│   ├── errors.py             # Structured error handling
│   ├── formatters.py         # Base markdown/JSON formatters
│   ├── models.py             # Shared Pydantic models + skill framework
│   ├── observability.py      # OTEL tracing and logging
│   ├── cache.py              # TTL-based tiered caching
│   └── shared_memory.py      # Inter-agent communication (ATP/in-memory)
│
├── tools/                    # Domain-specific tools
│   ├── __init__.py
│   ├── compute/              # Compute domain
│   │   ├── __init__.py
│   │   ├── models.py         # Input/output models
│   │   ├── tools.py          # Tool implementations
│   │   ├── formatters.py     # Compute-specific formatters
│   │   └── SKILL.md          # Domain documentation
│   ├── network/              # Network domain
│   ├── database/             # Database domain
│   ├── security/             # Security domain
│   ├── cost/                 # Cost/FinOps domain
│   └── observability/        # Monitoring/Logs domain
│
└── skills/                   # High-level workflow skills
    ├── __init__.py           # Skill registry and exports
    ├── agent.py              # Agent context, LLM sampling utilities
    ├── executor.py           # Skill executor with progress tracking
    ├── discovery.py          # Tool discovery and registry
    ├── tools.py              # Skill tool registration
    ├── troubleshoot.py       # Troubleshooting workflows
    └── SKILL.md              # Skills domain documentation
```

---

## 3. Tool Naming Convention

All tools follow the pattern: `oci_{domain}_{action}_{resource}`

| Pattern | Example | Description |
|---------|---------|-------------|
| `oci_{domain}_list_{resource}` | `oci_compute_list_instances` | List resources |
| `oci_{domain}_get_{resource}` | `oci_compute_get_instance` | Get single resource |
| `oci_{domain}_{action}_{resource}` | `oci_compute_start_instance` | Perform action |
| `oci_{domain}_analyze_{aspect}` | `oci_network_analyze_security` | Analysis workflow |

---

## 4. Tool Inventory

### 4.1 Discovery Tools (Tier 1 - Instant)

| Tool | Description | Latency |
|------|-------------|---------|
| `oci_ping` | Server health check | <50ms |
| `oci_list_domains` | List available capability domains | <50ms |
| `oci_search_tools` | Search for tools by keyword | <100ms |
| `oci_get_cache_stats` | Get cache performance statistics | <50ms |

### 4.2 Compute Tools

| Tool | Tier | Description |
|------|------|-------------|
| `oci_compute_list_instances` | 2 | List compute instances with filtering |
| `oci_compute_get_instance` | 2 | Get instance details with metrics |
| `oci_compute_start_instance` | 4 | Start a stopped instance |
| `oci_compute_stop_instance` | 4 | Stop a running instance |
| `oci_compute_restart_instance` | 4 | Restart an instance |

### 4.3 Network Tools

| Tool | Tier | Description |
|------|------|-------------|
| `oci_network_list_vcns` | 2 | List Virtual Cloud Networks |
| `oci_network_get_vcn` | 2 | Get VCN details |
| `oci_network_list_subnets` | 2 | List subnets in a VCN |
| `oci_network_list_security_lists` | 2 | List security lists |
| `oci_network_analyze_security` | 3 | Analyze security configuration |

### 4.4 Database Tools

| Tool | Tier | Description |
|------|------|-------------|
| `oci_database_list_autonomous` | 2 | List Autonomous Databases |
| `oci_database_get_autonomous` | 2 | Get ADB details |
| `oci_database_list_db_systems` | 2 | List DB Systems |
| `oci_database_get_db_system` | 2 | Get DB System details |
| `oci_database_list_mysql` | 2 | List MySQL instances |

### 4.5 Security Tools

| Tool | Tier | Description |
|------|------|-------------|
| `oci_security_list_users` | 2 | List IAM users |
| `oci_security_get_user` | 2 | Get user details |
| `oci_security_list_groups` | 2 | List IAM groups |
| `oci_security_list_policies` | 2 | List IAM policies |
| `oci_security_list_cloud_guard_problems` | 2 | List Cloud Guard problems |
| `oci_security_audit` | 3 | Comprehensive security audit |

### 4.6 Cost Tools

| Tool | Tier | Description |
|------|------|-------------|
| `oci_cost_get_summary` | 2 | Get cost summary for period |
| `oci_cost_by_service` | 2 | Get cost breakdown by service |
| `oci_cost_by_compartment` | 2 | Get cost by compartment |
| `oci_cost_monthly_trend` | 2 | Month-over-month trends |
| `oci_cost_detect_anomalies` | 3 | Detect cost anomalies |

### 4.7 Observability Tools

| Tool | Tier | Description |
|------|------|-------------|
| `oci_observability_get_instance_metrics` | 2 | Get instance metrics |
| `oci_observability_execute_log_query` | 3 | Execute Log Analytics query |
| `oci_observability_list_alarms` | 2 | List monitoring alarms |
| `oci_observability_get_alarm_history` | 2 | Get alarm history |
| `oci_observability_list_log_sources` | 2 | List log sources |
| `oci_observability_overview` | 3 | Observability dashboard |

### 4.8 Tool Aliases (Backward Compatibility)

For agents using shorter tool names, aliases are registered:

| Alias | Canonical Tool | Description |
|-------|----------------|-------------|
| `list_instances` | `oci_compute_list_instances` | List compute instances |
| `start_instance` | `oci_compute_start_instance` | Start a stopped instance |
| `stop_instance` | `oci_compute_stop_instance` | Stop a running instance |
| `restart_instance` | `oci_compute_restart_instance` | Restart an instance |
| `get_instance_metrics` | `oci_observability_get_instance_metrics` | Get instance metrics |

---

## 5. Authentication

The server supports multiple authentication methods:

```python
# Priority order
1. Instance Principal (for OCI compute instances)
2. Resource Principal (for OCI Functions)
3. Config File (~/.oci/config)
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OCI_CONFIG_FILE` | No | `~/.oci/config` | Path to OCI config |
| `OCI_CLI_PROFILE` | No | `DEFAULT` | Profile name |
| `OCI_REGION` | No | From config | Region override |
| `COMPARTMENT_OCID` | Yes | - | Default compartment |
| `ALLOW_MUTATIONS` | No | `false` | Enable write operations |
| `OCI_MCP_TRANSPORT` | No | `stdio` | Transport mode |
| `OCI_MCP_LOG_LEVEL` | No | `INFO` | Logging level |

---

## 6. Response Formats

All tools support dual response formats:

### Markdown (Default)
```python
list_instances(response_format="markdown")
```
Returns human-readable, context-efficient output:
```markdown
## Compute Instances (5)

| Name | State | Shape | IP |
|------|-------|-------|-----|
| web-01 | RUNNING | VM.Standard2.1 | 10.0.0.5 |
...
```

### JSON
```python
list_instances(response_format="json")
```
Returns machine-readable, complete data:
```json
{
  "total": 5,
  "instances": [
    {"id": "ocid1...", "display_name": "web-01", ...}
  ]
}
```

---

## 7. Error Handling

Errors are structured with actionable suggestions:

```python
@dataclass
class OCIError:
    category: ErrorCategory  # authentication, authorization, not_found, etc.
    message: str             # What went wrong
    suggestion: str          # How to fix it
    details: dict            # OCI request ID, status code, etc.
```

### Error Categories

| Category | HTTP Status | Description |
|----------|-------------|-------------|
| `authentication` | 401 | Invalid credentials |
| `authorization` | 403 | Missing IAM policies |
| `not_found` | 404 | Resource doesn't exist |
| `rate_limit` | 429 | Too many requests |
| `validation` | 400 | Invalid parameters |
| `service` | 500/503 | OCI service issue |
| `timeout` | - | Request timeout |

---

## 8. Tool Tiers

| Tier | Latency | Description | Examples |
|------|---------|-------------|----------|
| 1 | <100ms | Cached/instant | ping, search_tools |
| 2 | 100ms-1s | Single API call | list_instances |
| 3 | 1s-30s | Heavy analytics | detect_anomalies |
| 4 | Variable | Mutations | start_instance |

---

## 9. Caching Infrastructure

The server includes a tiered caching system optimized for OCI data volatility patterns:

### Cache Tiers

| Tier | TTL | Max Size | Use Case |
|------|-----|----------|----------|
| `static` | 1 hour | 500 | Rarely changing data (shapes, regions) |
| `config` | 5 min | 500 | Configuration data (compartments, VCNs) |
| `operational` | 1 min | 1000 | Operational data (instances, status) |
| `metrics` | 30 sec | 2000 | Real-time metrics and monitoring |

### Usage

```python
from mcp_server_oci.core import get_cache, cached

# Get a cache tier
cache = get_cache("operational")
await cache.set("key", value)
value = await cache.get("key")

# Use decorator for automatic caching
@cached(tier="config", ttl=300)
async def get_compartments():
    return await fetch_compartments()
```

### Cache Statistics

Use `oci_get_cache_stats` to monitor cache performance:
- Hit rate, hits, misses
- Evictions and expirations
- Current size per tier

---

## 10. Shared Memory (Inter-Agent Communication)

The server supports inter-agent communication through shared memory:

### Backends

| Backend | Description | Configuration |
|---------|-------------|---------------|
| `InMemorySharedStore` | In-process memory (default) | No config needed |
| `ATPSharedStore` | Oracle ATP database | `ATP_CONNECTION_STRING` env var |

### Features

- **Agent Registration**: Agents can register and track their state
- **Event Publishing**: Share findings and recommendations
- **Context Sharing**: Share conversation context between agents

### Usage

```python
from mcp_server_oci.core import get_shared_store, share_finding

# Get the shared store
store = get_shared_store()

# Share a finding
await share_finding(
    agent_id="troubleshooter",
    category="performance",
    severity="warning",
    message="High CPU detected on instance xyz"
)

# Get shared findings
findings = await get_shared_findings(category="performance")
```

---

## 11. Progressive Disclosure

The server implements progressive disclosure to avoid overwhelming LLM context:

1. **Start with Discovery**: Use `oci_list_domains()` to see available domains
2. **Search for Tools**: Use `oci_search_tools(query="cost")` to find relevant tools
3. **Get Tool Schema**: Each tool has typed input parameters
4. **Execute with Pagination**: Use `limit` and `offset` for large result sets

```python
# Discovery flow
oci_list_domains()                    # See: compute, network, database, ...
oci_search_tools(query="instances")   # Find: oci_compute_list_instances
oci_compute_list_instances(limit=10)  # Get first 10 instances
```

---

## 10. Adding New Tools

### Step 1: Create Domain Directory
```
tools/new_domain/
├── __init__.py
├── models.py      # Pydantic input/output models
├── tools.py       # Tool implementations
└── formatters.py  # Markdown formatters
```

### Step 2: Define Input Model
```python
# models.py
class ListResourcesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    compartment_id: str = Field(..., description="Compartment OCID")
    limit: int = Field(default=20, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
```

### Step 3: Implement Tool
```python
# tools.py
def register_new_domain_tools(mcp: FastMCP) -> None:

    @mcp.tool(
        name="oci_newdomain_list_resources",
        annotations={
            "title": "List Resources",
            "readOnlyHint": True,
            "destructiveHint": False,
        }
    )
    async def list_resources(params: ListResourcesInput, ctx: Context) -> str:
        """List resources in a compartment."""
        # Implementation
```

### Step 4: Register in Server
```python
# server.py
from mcp_server_oci.tools.new_domain.tools import register_new_domain_tools

register_new_domain_tools(mcp)
```

---

## 14. Skills Architecture

Skills are high-level operations that orchestrate multiple tools.

### Skill Executor Framework

The `SkillExecutor` provides a robust framework for building skills:

```python
from mcp_server_oci.skills import SkillExecutor, register_skill

@register_skill("troubleshoot_instance")
class TroubleshootInstanceSkill:
    """Multi-step instance troubleshooting workflow."""

    async def execute(self, executor: SkillExecutor, params: dict) -> str:
        # Report progress
        await executor.report_progress(0.1, "Fetching instance details...")

        # Call other tools
        instance = await executor.call_tool(
            "oci_compute_get_instance",
            {"instance_id": params["instance_id"]}
        )

        await executor.report_progress(0.4, "Analyzing metrics...")
        metrics = await executor.call_tool(
            "oci_observability_get_instance_metrics",
            {"instance_id": params["instance_id"]}
        )

        # Use LLM for analysis (if configured)
        analysis = await executor.analyze(
            data={"instance": instance, "metrics": metrics},
            prompt="Analyze this instance health and provide recommendations"
        )

        return executor.format_result(analysis)
```

### Skill Registry

Skills are automatically registered and discoverable:

```python
from mcp_server_oci.skills import list_skills, get_skill_registry

# List all registered skills
skills = list_skills()

# Get specific skill metadata
registry = get_skill_registry()
skill_info = registry.get("troubleshoot_instance")
```

### Agent Context

For skills that need LLM capabilities:

```python
from mcp_server_oci.skills import AgentContext, SamplingClient

# Create agent context
context = AgentContext(
    agent_id="my_skill",
    sampling_client=SamplingClient(ctx)  # From MCP context
)

# Use for analysis
result = await context.analyze(data, prompt)
```

---

## 15. Recent Changes (v2.3.0)

### Code Quality Improvements
- Fixed `ResponseFormat` enum duplication (now canonical in `core/formatters.py`)
- Fixed `report_progress()` signature to match FastMCP API
- Fixed `get_client_manager()` async/sync handling
- Added `__all__` exports to `core/models.py`
- Configured mypy to ignore OCI SDK stub errors
- Reduced ruff errors from 1484 to ~333 (mostly line-length)
- Reduced mypy errors from 402 to ~290

### Framework Enhancements
- Skills framework with `SkillExecutor`, `AgentContext`, `SamplingClient`
- TTL-based tiered caching (`cache.py`)
- Inter-agent shared memory (`shared_memory.py`)
- Improved error handling with string/OCIError flexibility

---

## 16. Planned Enhancements

### Phase 1: Critical Services (Q1)
- [ ] Object Storage tools
- [ ] Block Storage tools
- [ ] Load Balancer tools
- [ ] Vault/Secrets tools

### Phase 2: Container & Serverless (Q2)
- [ ] Container Engine (OKE) tools
- [ ] Functions tools
- [ ] API Gateway tools

### Phase 3: Advanced Features (Q3) - Mostly Complete
- [ ] Streaming/Events tools
- [ ] Resource Manager (IaC) tools
- [x] Enhanced skills and workflows (SkillExecutor framework)
- [x] Caching layer (TTL-based tiered caching)
- [x] Inter-agent communication (shared memory)
- [x] Error handling improvements
- [ ] OpenTelemetry integration (partial - logging complete)

---

## 17. Testing

```bash
# Install dependencies
uv sync

# Run server locally
uv run python -m mcp_server_oci.server

# Run smoke tests
uv run python tests/smoke_test.py

# Run full test suite
uv run pytest tests/

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```

---

## 18. Related Documentation

- [SKILL.md](./SKILL.md) - Skill definition for AI agents
- [REVIEW.md](./REVIEW.md) - Comprehensive review and improvement plan
- [CLAUDE.md](./CLAUDE.md) - Claude Code instructions
- [docs/BUILD_MCP_SERVER.md](./docs/BUILD_MCP_SERVER.md) - Guide for building OCI MCP servers
- [docs/BUILD_OCI_AGENTS.md](./docs/BUILD_OCI_AGENTS.md) - Guide for building OCI agents
