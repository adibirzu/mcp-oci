# CLAUDE.md

This file provides guidance to Claude Code and other AI assistants when working with this codebase.

## Project Overview

OCI MCP Server is a Model Context Protocol server and multi-backend gateway for Oracle Cloud Infrastructure. It provides AI agents with comprehensive OCI management capabilities through progressive disclosure and context-efficient tools, plus an aggregating gateway that proxies multiple MCP servers through a single authenticated endpoint.

**Key components:**
- **OCI MCP Server** - FastMCP server with 6 tool domains (Compute, Cost, Database, Network, Observability, Security)
- **MCP Gateway** - Aggregating reverse proxy with OAuth 2.1 auth, auto-discovery, and health monitoring
- **Skills Framework** - High-level workflow skills combining multiple tools (troubleshooting, runbooks)

## Commands

### Development
```bash
uv sync                           # Install dependencies
uv sync --all-extras              # Install all extras (gateway, otel, dev)
uv run python -m mcp_server_oci.server  # Run MCP server (stdio)
uv run python -m mcp_server_oci.gateway # Run MCP Gateway (streamable HTTP)
uv run python tests/smoke_test.py       # Run smoke tests
```

### Gateway
```bash
# Run gateway with config file
uv run oci-mcp-gateway --config gateway.json

# Run gateway with CLI options
uv run oci-mcp-gateway --port 9000 --no-auth --log-level DEBUG

# Run gateway with environment variables
MCP_GATEWAY_CONFIG=gateway.json MCP_GATEWAY_PORT=9000 uv run oci-mcp-gateway

# Discover MCP servers from directories
uv run oci-mcp-gateway --scan ~/projects --discover-only

# Load backend configs from a drop-in directory
uv run oci-mcp-gateway --backends-dir ./backends.d

# Scan + run (discovered backends are disabled by default)
uv run oci-mcp-gateway --config gateway.json --scan ~/projects
```

### Code Quality
```bash
uv run ruff check src/            # Linting
uv run mypy src/                  # Type checking
uv run pytest tests/              # Unit tests
```

## Architecture

```
src/mcp_server_oci/
├── __init__.py             # Package init (version 2.0.0)
├── __main__.py             # Server module entry point
├── server.py               # FastMCP entry point, tool registration, app lifespan
├── config.py               # Environment configuration (AuthMethod, TransportType, AppConfig)
├── core/
│   ├── client.py           # OCI SDK client manager (async, multi-auth, lazy init)
│   ├── errors.py           # Structured OCIError with categories and suggestions
│   ├── formatters.py       # Markdown/JSON response formatters (Formatter, MarkdownFormatter)
│   ├── models.py           # Base Pydantic models (pagination, time ranges, skills)
│   ├── observability.py    # OpenTelemetry tracing + structured logging (stderr)
│   ├── cache.py            # TTL-based caching (in-memory LRU + Redis, 4 tiers)
│   └── shared_memory.py    # Inter-agent shared store (in-memory + Oracle ATP)
├── gateway/
│   ├── __init__.py         # Package exports (config, discovery, registry, server, auth)
│   ├── __main__.py         # Gateway CLI (--config, --scan, --backends-dir, --discover-only)
│   ├── config.py           # Gateway + backend configuration models
│   ├── discovery.py        # Auto-discovery of MCP servers from dirs/projects
│   ├── auth.py             # OAuth 2.1 / Bearer token auth (JWT + static tokens)
│   ├── registry.py         # Backend lifecycle + health monitoring (quarantine/recovery)
│   └── server.py           # Gateway proxy aggregation, routing, audit logging
├── tools/
│   ├── discovery.py        # Progressive disclosure: search_tools, list_domains
│   ├── compute/            # Compute domain (instances, metrics, start/stop/restart)
│   │   ├── models.py       # Input models (ListInstancesInput, etc.)
│   │   ├── tools.py        # Tool implementations with @mcp.tool
│   │   ├── actions.py      # Instance actions (start, stop, reboot)
│   │   ├── list.py         # Instance and shape listing
│   │   └── formatters.py   # Compute-specific formatters
│   ├── cost/               # Cost/FinOps domain (summaries, trends, anomalies)
│   ├── database/           # Database domain (management, backups)
│   ├── network/            # Network domain (VCNs, subnets, security lists)
│   ├── observability/      # Monitoring domain (logs, metrics, alarms)
│   │   ├── logs.py         # Logging service tools
│   │   └── metrics.py      # Metrics service tools
│   └── security/           # Security domain (policies, IAM)
└── skills/
    ├── troubleshoot.py     # Compute instance troubleshooting skill
    ├── troubleshoot_database.py  # Database troubleshooting skill
    ├── agent.py            # Agent orchestration
    ├── executor.py         # Skill step execution with error handling
    ├── runbooks.py         # Predefined runbook workflows
    ├── discovery.py        # Skill catalog discovery
    └── tools.py            # Skill tool registration
```

## Entry Points

Defined in `pyproject.toml`:
- `oci-mcp` → `mcp_server_oci.server:main` (OCI MCP Server)
- `oci-mcp-gateway` → `mcp_server_oci.gateway.__main__:main` (MCP Gateway)

## Dependencies

| Group | Key Packages |
|-------|-------------|
| **Core** | `mcp>=1.0.0`, `fastmcp>=2.14.1`, `oci>=2.164.2`, `pydantic>=2.5.0`, `httpx>=0.25.0`, `structlog>=24.0.0`, `redis>=5.0.0`, `python-dotenv>=1.0.0` |
| **Gateway** | `PyJWT[crypto]>=2.8.0` |
| **OTEL** | `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation-httpx` |
| **Dev** | `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `pytest-cov>=4.1.0`, `ruff>=0.3.0`, `mypy>=1.8.0` |

Python requirement: `>=3.12`

## MCP Gateway

The gateway is an aggregating reverse proxy that exposes multiple backend MCP
servers through a single Streamable HTTP endpoint with OAuth/Bearer authentication.

### Architecture
```
                      ┌──────────────────────────────────────────────┐
                      │            MCP Gateway (:9000/mcp)           │
                      │                                              │
Agent (OAuth Bearer)──│  Auth ──▶ Route ──▶ Proxy ──▶ Audit         │
                      │                                              │
                      └────┬──────────┬──────────┬──────────┬───────┘
                           │          │          │          │
                           ▼          ▼          ▼          ▼
                      OCI MCP     Remote MCP   External    In-Process
                      (stdio)     (HTTP+OAuth)  Servers     Servers
                                               (stdio)
```

### Key Features
- **Streamable HTTP** transport for the client-facing endpoint (MCP 2025-06-18+)
- **OAuth 2.1 / Bearer token** authentication (JWT or static tokens)
- **Multi-transport backends**: stdio, streamable HTTP, or in-process
- **Multi-auth backends**: .oci/config, resource principals, instance principals, bearer tokens
- **Tool namespacing**: Backend tools prefixed to avoid collisions
- **Health monitoring**: Automatic health checks with quarantine/recovery
- **Audit logging**: All tool invocations logged with client identity
- **Per-tool access control**: Scope-based authorization per tool
- **Auto-discovery**: Scan directories for MCP servers (.mcp.json, pyproject.toml, FastMCP scripts)
- **Multi-project support**: Backends from different folders/repos with independent venvs and PYTHONPATH
- **Drop-in config**: Load backend definitions from a `backends.d/` directory

### Backend Transport Types
| Transport | Use Case | Connection |
|-----------|----------|------------|
| `stdio` | Local MCP servers | Spawns subprocess |
| `streamable_http` | Remote MCP servers | HTTP client |
| `in_process` | Same-process servers | Direct import |

### Backend Authentication Methods
| Method | Use Case | Config |
|--------|----------|--------|
| `oci_config` | Local development | `~/.oci/config` file |
| `resource_principal` | OKE / Functions | Auto-detected |
| `instance_principal` | Compute instances | Auto-detected |
| `bearer_token` | Remote MCP servers | Token in config |
| `api_key` | OCI API key | Key in config |
| `none` | No auth needed | - |

### Gateway Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_GATEWAY_CONFIG` | - | Path to gateway JSON config |
| `MCP_GATEWAY_HOST` | `0.0.0.0` | Listen address |
| `MCP_GATEWAY_PORT` | `9000` | Listen port |
| `MCP_GATEWAY_PATH` | `/mcp` | Endpoint path |
| `MCP_GATEWAY_NAME` | `oci-mcp-gateway` | Gateway server name |
| `MCP_GATEWAY_AUTH_ENABLED` | `true` | Enable OAuth/Bearer auth |
| `MCP_GATEWAY_JWT_PUBLIC_KEY` | - | Path to JWT public key PEM |
| `MCP_GATEWAY_JWT_ISSUER` | - | Expected JWT issuer |
| `MCP_GATEWAY_JWT_AUDIENCE` | - | Expected JWT audience |
| `MCP_GATEWAY_LOG_LEVEL` | `INFO` | Log level |
| `MCP_GATEWAY_BACKENDS_DIR` | - | Directory of backend config fragments |
| `MCP_GATEWAY_SCAN_PATHS` | - | Colon-separated dirs to scan for MCP servers |

### Gateway CLI Options
```
--config, -c FILE     Gateway JSON config file
--host HOST           Listen address (default: 0.0.0.0)
--port, -p PORT       Listen port (default: 9000)
--path PATH           MCP endpoint path (default: /mcp)
--no-auth             Disable authentication
--stateless           Stateless mode for horizontal scaling
--log-level LEVEL     DEBUG|INFO|WARNING|ERROR
--scan DIR            Scan directory for MCP servers (repeatable)
--backends-dir DIR    Load backend config fragments from *.json files
--discover-only       Print discovered backends as JSON and exit
```

### Auto-Discovery

The gateway can discover MCP servers from external projects:

```bash
# Scan directories for MCP servers (prints JSON, does not start)
oci-mcp-gateway --scan ~/projects --discover-only

# Discovered backends are disabled by default for operator review
# Enable them in gateway.json or via backends.d/ drop-in configs
```

Discovery checks for:
1. `.mcp.json` / `mcp.json` -- standard MCP client config (authoritative)
2. `pyproject.toml` -- projects with MCP-related entry points
3. `server.py` / `main.py` / `app.py` -- Python files with FastMCP patterns
4. `src/` layout -- packages with `server.py` inside `src/<pkg>/`

External project backends support:
- **`venv`**: Path to virtual environment (gateway uses its Python binary)
- **`pythonpath`**: Additional PYTHONPATH entries for the backend process
- **`cwd`**: Working directory for the backend subprocess
- **`tags`**: Categorization labels (e.g. `auto-discovered`, `project:name`)

### Health Monitoring

The registry runs background health checks per backend:
- **Healthy**: Responding normally
- **Degraded**: 1-2 consecutive failures
- **Unhealthy**: 3+ consecutive failures (quarantined)
- Recovery: Automatic on next successful check

### Gateway Management Tools
- `gateway_health` -- JSON health status of gateway and all backends
- `gateway_list_backends` -- Markdown list of backends with status
- `gateway_audit_log` -- Recent tool invocations with client identity

## Key Patterns

### Tool Registration (FastMCP)
```python
@mcp.tool(
    name="oci_domain_action_resource",
    annotations={
        "title": "Human Title",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def my_tool(params: InputModel, ctx: Context) -> str:
    """Tool docstring with full description."""
```

### Input Models (Pydantic v2)
```python
class MyInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    required_field: str = Field(..., description="Description")
    optional_field: Optional[str] = Field(default=None)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
```

### Error Handling
```python
try:
    result = await oci_operation()
except Exception as e:
    error = handle_oci_error(e, "context description")
    return format_error_response(error, params.response_format)
```

### Response Formats
- **Markdown**: Human-readable, context-efficient summaries
- **JSON**: Machine-readable, complete structured data

## Environment Variables

### OCI MCP Server
| Variable | Default | Description |
|----------|---------|-------------|
| `OCI_CONFIG_FILE` | `~/.oci/config` | OCI SDK config path |
| `OCI_CLI_PROFILE` | `DEFAULT` | OCI profile name |
| `OCI_REGION` | From config | Override region |
| `OCI_TENANCY_OCID` | From config | Override tenancy |
| `COMPARTMENT_OCID` | - | Default compartment |
| `ALLOW_MUTATIONS` | `false` | Enable write ops |
| `OCI_MCP_TRANSPORT` | `stdio` | Transport mode (`stdio` or `streamable_http`) |
| `OCI_MCP_PORT` | `8000` | HTTP port (streamable_http only) |
| `OCI_MCP_LOG_LEVEL` | `INFO` | Logging level |
| `REDIS_URL` | - | Redis URL for caching (fallback: in-memory) |

### Observability
| Variable | Default | Description |
|----------|---------|-------------|
| `OCI_APM_ENDPOINT` | - | OCI APM data upload endpoint |
| `OCI_APM_PRIVATE_DATA_KEY` | - | APM private data key |
| `OCI_APM_DOMAIN_ID` | - | APM domain OCID |
| `OCI_LOGGING_ENABLED` | `false` | Enable OCI Logging |
| `OCI_LOGGING_LOG_ID` | - | Log OCID for ingestion |
| `OCI_LOGAN_NAMESPACE` | - | Log Analytics namespace |
| `OCI_LOGAN_LOG_GROUP_ID` | - | Log Analytics log group OCID |

## CI/CD

Three GitHub Actions workflows in `.github/workflows/`:

| Workflow | File | Trigger | What it does |
|----------|------|---------|-------------|
| **CI** | `ci.yml` | Push/PR to main | Ruff lint + mypy type check + pytest with coverage. Matrix: Python 3.12/3.13 on Linux, macOS, Windows. Uses `uv sync --all-extras`. |
| **Integration** | `integration.yml` | Manual / `integration-*` tags | Integration tests against live OCI (Python 3.12, ubuntu). Requires `OCI_CONFIG_B64` and `TEST_OCI_TENANCY_OCID` secrets. |
| **Secret Scan** | `secret-scan.yml` | Push/PR | Gitleaks in Docker with `.gitleaks.toml`. Uploads SARIF to GitHub Security tab + JSON artifact. |

## Adding New Tools

1. **Create domain directory** under `tools/`
2. **Create models.py** with Pydantic input models
3. **Create tools.py** with @mcp.tool decorated functions
4. **Create formatters.py** for markdown output
5. **Create SKILL.md** with domain documentation
6. **Register in server.py** via `register_*_tools(mcp)`

## Tool Tiers

| Tier | Latency | Description | Examples |
|------|---------|-------------|----------|
| 1 | <100ms | Cached/instant | ping, search_tools |
| 2 | 100ms-1s | Single API call | list_instances |
| 3 | 1s-30s | Heavy analytics | detect_anomalies |
| 4 | Variable | Admin/write ops | start_instance |

## Important Notes

- **No hardcoded credentials** - All sensitive data via environment
- **Mutations disabled by default** - Set ALLOW_MUTATIONS=true to enable
- **Progressive disclosure** - Use search_tools before listing all tools
- **Pagination required** - All list tools support limit/offset
- **Both formats required** - Tools must support markdown AND json
- **Python 3.12+ required** - Uses StrEnum, `X | Y` union syntax, and other 3.12+ features
- **uv for dependency management** - All commands use `uv run` / `uv sync`
