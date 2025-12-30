# OCI MCP Server

A professional-grade Oracle Cloud Infrastructure (OCI) MCP server built with FastMCP, implementing Anthropic's best practices for AI agent tool integration.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.0-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Progressive Disclosure** - Tools are discoverable on-demand, not loaded upfront
- **Dual Response Formats** - Markdown (human-readable) and JSON (machine-readable)
- **Skills Architecture** - High-level workflow skills combining multiple tools
- **Context Efficiency** - Pagination, filtering, and summarization built-in
- **Multiple Domains** - Cost, Compute, Observability (extensible to more)
- **Secure by Default** - Environment-based configuration, no hardcoded credentials

## Quick Start

### Prerequisites

- Python 3.11+
- OCI CLI configured (`~/.oci/config`)
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/mcp-oci-new.git
cd mcp-oci-new

# Create virtual environment and install dependencies
uv sync

# Copy and configure environment
cp .env.example .env.local
# Edit .env.local with your settings
```

### Configuration

Configure your environment in `.env.local`:

```bash
# Required: OCI SDK configuration
OCI_CONFIG_FILE=~/.oci/config
OCI_CLI_PROFILE=DEFAULT

# Optional: Override region/tenancy
# OCI_REGION=us-ashburn-1
# OCI_TENANCY_OCID=ocid1.tenancy.oc1..xxx
```

### Running the Server

```bash
# Standard I/O mode (for MCP clients)
uv run python -m mcp_server_oci.server

# HTTP mode (for testing/debugging)
OCI_MCP_TRANSPORT=streamable_http uv run python -m mcp_server_oci.server
```

### MCP Client Configuration

Add to your MCP client configuration (e.g., Claude Desktop, Cline):

```json
{
  "mcpServers": {
    "oci-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-oci-new", "python", "-m", "mcp_server_oci.server"],
      "env": {
        "OCI_CLI_PROFILE": "DEFAULT"
      }
    }
  }
}
```

## Architecture

```
src/mcp_server_oci/
├── server.py              # FastMCP server entry point
├── config.py              # Configuration management
├── core/
│   ├── client.py          # OCI SDK client wrapper
│   ├── errors.py          # Structured error handling
│   ├── formatters.py      # Response formatters
│   ├── models.py          # Base Pydantic models
│   └── observability.py   # Tracing and logging
├── tools/
│   ├── discovery.py       # Tool discovery (search_tools, list_domains)
│   ├── compute/           # Compute domain tools
│   ├── cost/              # Cost/FinOps domain tools
│   └── observability/     # Monitoring/Logging tools
└── skills/
    └── troubleshoot.py    # High-level workflow skills
```

## Available Tools

### Discovery Tools
| Tool | Description |
|------|-------------|
| `oci_search_tools` | Search for tools by keyword with detail levels |
| `oci_list_domains` | List available OCI tool domains |
| `oci_get_tool_schema` | Get complete schema for a specific tool |
| `oci_ping` | Health check and connectivity test |

### Compute Domain
| Tool | Description |
|------|-------------|
| `oci_compute_list_instances` | List compute instances with filtering |
| `oci_compute_start_instance` | Start a stopped instance |
| `oci_compute_stop_instance` | Stop a running instance |
| `oci_compute_restart_instance` | Restart an instance |
| `oci_compute_get_metrics` | Get instance performance metrics |

### Cost Domain
| Tool | Description |
|------|-------------|
| `oci_cost_get_summary` | Get cost summary for time period |
| `oci_cost_by_compartment` | Cost breakdown by compartment |
| `oci_cost_by_service` | Cost breakdown by OCI service |
| `oci_cost_monthly_trend` | Monthly trend with forecast |
| `oci_cost_detect_anomalies` | Detect cost spikes and anomalies |

### Observability Domain
| Tool | Description |
|------|-------------|
| `oci_observability_get_metrics` | Query OCI Monitoring metrics |
| `oci_observability_get_logs` | Query Logging Analytics |
| `oci_observability_list_alarms` | List monitoring alarms |

### Skills (Workflows)
| Skill | Description |
|-------|-------------|
| `oci_skill_troubleshoot_instance` | Comprehensive instance troubleshooting |

## Usage Examples

### Progressive Discovery
```python
# 1. Search for relevant tools
result = await oci_search_tools(query="cost", detail_level="summary")

# 2. Get full schema for selected tool
schema = await oci_get_tool_schema(tool_name="oci_cost_get_summary")

# 3. Execute the tool
summary = await oci_cost_get_summary(
    tenancy_ocid="ocid1.tenancy...",
    time_start="2024-01-01T00:00:00Z",
    time_end="2024-01-31T23:59:59Z",
    response_format="markdown"
)
```

### Response Formats
```python
# Human-readable markdown (default)
result = await oci_compute_list_instances(
    compartment_id="ocid1.compartment...",
    response_format="markdown"
)
# Returns: "## Instances\n| Name | State | Shape |..."

# Machine-readable JSON
result = await oci_compute_list_instances(
    compartment_id="ocid1.compartment...",
    response_format="json"
)
# Returns: {"items": [...], "total": 10, "has_more": false}
```

## Development

### Running Tests

```bash
# Unit tests
uv run pytest tests/

# Smoke test (tool registration check)
uv run python tests/smoke_test.py
```

### Code Quality

```bash
# Linting
uv run ruff check src/

# Type checking
uv run mypy src/
```

### Adding a New Domain

1. Create directory structure:
   ```
   src/mcp_server_oci/tools/newdomain/
   ├── __init__.py
   ├── SKILL.md
   ├── models.py
   ├── tools.py
   └── formatters.py
   ```

2. Register in `server.py`:
   ```python
   from mcp_server_oci.tools.newdomain.tools import register_newdomain_tools
   register_newdomain_tools(mcp)
   ```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OCI_CONFIG_FILE` | No | `~/.oci/config` | Path to OCI config file |
| `OCI_CLI_PROFILE` | No | `DEFAULT` | OCI config profile name |
| `OCI_REGION` | No | From config | Override region |
| `OCI_TENANCY_OCID` | No | From config | Override tenancy |
| `COMPARTMENT_OCID` | No | - | Default compartment |
| `ALLOW_MUTATIONS` | No | `false` | Enable write operations |
| `OCI_MCP_TRANSPORT` | No | `stdio` | Transport: stdio or streamable_http |
| `OCI_MCP_PORT` | No | `8000` | HTTP port (if using HTTP transport) |
| `OCI_MCP_LOG_LEVEL` | No | `INFO` | Logging level |

## Security

- **No hardcoded credentials** - All sensitive data via environment variables
- **Config file isolation** - Uses OCI SDK standard config locations
- **Mutation protection** - Write operations disabled by default
- **Input validation** - Pydantic v2 models with strict validation

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read the [CONTRIBUTING](CONTRIBUTING.md) guide first.

## Related Resources

- [OCI MCP Server Standard v2.0](docs/OCI_MCP_SERVER_STANDARD_V2_1.md)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [OCI SDK for Python](https://docs.oracle.com/en-us/iaas/tools/python/latest/)
