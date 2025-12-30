# CLAUDE.md

This file provides guidance to Claude Code and other AI assistants when working with this codebase.

## Project Overview

OCI MCP Server is a Model Context Protocol server for Oracle Cloud Infrastructure. It provides AI agents with comprehensive OCI management capabilities through progressive disclosure and context-efficient tools.

## Commands

### Development
```bash
uv sync                           # Install dependencies
uv run python -m mcp_server_oci.server  # Run server (stdio)
uv run python tests/smoke_test.py       # Run smoke tests
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
