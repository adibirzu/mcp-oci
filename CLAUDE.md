# CLAUDE.md

This file provides guidance to Claude Code and other AI assistants when working with this codebase.

## Project Overview

OCI MCP Server is a Model Context Protocol server for Oracle Cloud Infrastructure. It provides AI agents with comprehensive OCI management capabilities through progressive disclosure and context-efficient tools.

## Commands

### Development
```bash
uv sync                           # Install dependencies
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
├── server.py           # FastMCP entry point, tool registration
├── config.py           # Environment configuration with Pydantic
├── core/
│   ├── client.py       # OCI SDK client wrapper with auth handling
│   ├── errors.py       # Structured OCIError with suggestions
│   ├── formatters.py   # Markdown/JSON response formatters
│   ├── models.py       # Base Pydantic models (ResponseFormat, etc.)
│   └── observability.py # OTEL tracing and structured logging
├── gateway/            # MCP Gateway (aggregating proxy)
│   ├── __init__.py     # Package exports
│   ├── __main__.py     # CLI entry point
│   ├── config.py       # Gateway + backend configuration models
│   ├── discovery.py    # Auto-discovery of MCP servers from dirs/projects
│   ├── auth.py         # OAuth/Bearer authentication provider
│   ├── registry.py     # Backend server registry + health monitoring
│   └── server.py       # Gateway server (proxy aggregation, routing)
├── tools/
│   ├── discovery.py    # Progressive disclosure: search_tools, list_domains
│   ├── compute/        # Compute domain tools
│   │   ├── models.py   # Input models (ListInstancesInput, etc.)
│   │   ├── tools.py    # Tool implementations with @mcp.tool
│   │   └── formatters.py # Compute-specific formatters
│   ├── cost/           # Cost/FinOps domain tools
│   └── observability/  # Monitoring/Logging tools
└── skills/
    └── troubleshoot.py # High-level workflow skills
```

## MCP Gateway

The gateway is an aggregating reverse proxy that exposes multiple backend MCP
servers through a single Streamable HTTP endpoint with OAuth/Bearer authentication.

### Architecture
```
Agent (OAuth Bearer) --> [Gateway :9000/mcp] --> Backend A (stdio, .oci/config)
                                              --> Backend B (HTTP, resource principal)
                                              --> Backend C (in-process)
                                              --> External MCP servers
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
| `none` | No auth needed | - |

### Gateway Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_GATEWAY_CONFIG` | - | Path to gateway JSON config |
| `MCP_GATEWAY_HOST` | `0.0.0.0` | Listen address |
| `MCP_GATEWAY_PORT` | `9000` | Listen port |
| `MCP_GATEWAY_PATH` | `/mcp` | Endpoint path |
| `MCP_GATEWAY_AUTH_ENABLED` | `true` | Enable OAuth/Bearer auth |
| `MCP_GATEWAY_JWT_PUBLIC_KEY` | - | Path to JWT public key PEM |
| `MCP_GATEWAY_JWT_ISSUER` | - | Expected JWT issuer |
| `MCP_GATEWAY_JWT_AUDIENCE` | - | Expected JWT audience |
| `MCP_GATEWAY_LOG_LEVEL` | `INFO` | Log level |
| `MCP_GATEWAY_BACKENDS_DIR` | - | Directory of backend config fragments |
| `MCP_GATEWAY_SCAN_PATHS` | - | Colon-separated dirs to scan for MCP servers |

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

| Variable | Default | Description |
|----------|---------|-------------|
| `OCI_CONFIG_FILE` | `~/.oci/config` | OCI SDK config path |
| `OCI_CLI_PROFILE` | `DEFAULT` | OCI profile name |
| `OCI_REGION` | From config | Override region |
| `ALLOW_MUTATIONS` | `false` | Enable write ops |
| `OCI_MCP_TRANSPORT` | `stdio` | Transport mode |
| `OCI_MCP_LOG_LEVEL` | `INFO` | Logging level |

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
