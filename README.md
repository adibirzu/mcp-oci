# OCI MCP Server

A production-grade Oracle Cloud Infrastructure (OCI) MCP server and multi-backend gateway built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk), implementing the [Model Context Protocol](https://modelcontextprotocol.io/) (2025-06-18+) for AI agent tool integration.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-2025--06--18-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

### OCI MCP Server
- **Progressive Disclosure** - Tools are discoverable on-demand via `search_tools` / `list_domains`
- **Dual Response Formats** - Markdown (human-readable) and JSON (machine-readable)
- **Six Tool Domains** - Compute, Cost, Database, Network, Observability, Security
- **Skills Architecture** - High-level workflow skills combining multiple tools
- **Context Efficiency** - Pagination, filtering, and summarization built-in
- **Secure by Default** - Environment-based configuration, no hardcoded credentials, mutations disabled by default

### MCP Gateway
- **Aggregating Reverse Proxy** - Expose multiple MCP servers through a single Streamable HTTP endpoint
- **OAuth 2.1 / Bearer Token Auth** - JWT verification or static tokens for development
- **Multi-Transport Backends** - Connect to servers via stdio, Streamable HTTP, or in-process
- **Auto-Discovery** - Scan directories for MCP servers (`.mcp.json`, `pyproject.toml`, FastMCP patterns)
- **Multi-Project Support** - Backends from different folders/repos with independent venvs and PYTHONPATH
- **Health Monitoring** - Automatic health checks with quarantine and recovery
- **Audit Logging** - All tool invocations logged with client identity
- **Drop-in Config** - Load backend definitions from a `backends.d/` directory

## Quick Start

### Prerequisites

- Python 3.12+
- OCI CLI configured (`~/.oci/config`)
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/adibirzu/mcp-oci.git
cd mcp-oci

# Install dependencies
uv sync

# Install with gateway extras (JWT support)
uv sync --extra gateway

# Install with all extras
uv sync --all-extras
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

# Optional: Enable write operations (disabled by default)
# ALLOW_MUTATIONS=true
```

### Running the OCI MCP Server

```bash
# Standard I/O mode (for MCP clients like Claude Desktop, Cursor, etc.)
uv run python -m mcp_server_oci.server

# Streamable HTTP mode (for remote access)
OCI_MCP_TRANSPORT=streamable_http uv run python -m mcp_server_oci.server
```

### Running the MCP Gateway

```bash
# Run gateway with config file
uv run oci-mcp-gateway --config gateway.json

# Run with CLI options
uv run oci-mcp-gateway --port 9000 --no-auth --log-level DEBUG

# Discover MCP servers from project directories
uv run oci-mcp-gateway --scan ~/projects --discover-only

# Run gateway with auto-discovered + configured backends
uv run oci-mcp-gateway --config gateway.json --scan ~/projects
```

### MCP Client Configuration

Add to your MCP client configuration (e.g., Claude Desktop, Cursor, Cline):

```json
{
  "mcpServers": {
    "oci-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-oci", "python", "-m", "mcp_server_oci.server"],
      "env": {
        "OCI_CLI_PROFILE": "DEFAULT"
      }
    }
  }
}
```

Or connect through the gateway for multi-server aggregation:

```json
{
  "mcpServers": {
    "oci-gateway": {
      "url": "http://localhost:9000/mcp",
      "headers": {
        "Authorization": "Bearer <your-token>"
      }
    }
  }
}
```

## Architecture

```
src/mcp_server_oci/
├── __init__.py             # Package init (version 2.0.0)
├── __main__.py             # Server module entry point
├── server.py               # FastMCP server entry point, tool registration
├── config.py               # Environment configuration (Pydantic)
├── core/
│   ├── client.py           # OCI SDK client manager (async, multi-auth)
│   ├── errors.py           # Structured OCIError with suggestions
│   ├── formatters.py       # Markdown/JSON response formatters
│   ├── models.py           # Base Pydantic models (pagination, time ranges, etc.)
│   ├── observability.py    # OpenTelemetry tracing + structured logging
│   ├── cache.py            # TTL-based caching (in-memory + Redis)
│   └── shared_memory.py    # Inter-agent shared store (in-memory + Oracle ATP)
├── gateway/
│   ├── __main__.py         # Gateway CLI entry point
│   ├── config.py           # Gateway + backend configuration models
│   ├── discovery.py        # Auto-discovery of MCP servers from directories
│   ├── auth.py             # OAuth 2.1 / Bearer token authentication
│   ├── registry.py         # Backend lifecycle + health monitoring
│   └── server.py           # Gateway proxy aggregation + audit logging
├── tools/
│   ├── discovery.py        # Progressive disclosure (search_tools, list_domains)
│   ├── compute/            # Compute domain (instances, metrics, actions)
│   ├── cost/               # Cost/FinOps domain (summaries, trends, anomalies)
│   ├── database/           # Database domain (management, backups)
│   ├── network/            # Network domain (VCNs, subnets, security lists)
│   ├── observability/      # Monitoring domain (logs, metrics, alarms)
│   └── security/           # Security domain (policies, IAM)
└── skills/
    ├── troubleshoot.py     # Compute instance troubleshooting skill
    ├── troubleshoot_database.py  # Database troubleshooting skill
    ├── agent.py            # Agent orchestration
    ├── executor.py         # Skill step execution
    ├── runbooks.py         # Predefined runbook workflows
    └── discovery.py        # Skill catalog discovery
```

## MCP Gateway

The gateway is an aggregating reverse proxy that exposes multiple backend MCP servers through a single Streamable HTTP endpoint with OAuth/Bearer authentication.

### Gateway Architecture

```
                          ┌──────────────────────────────────────────────┐
                          │            MCP Gateway (:9000/mcp)           │
                          │                                              │
Agent ──(OAuth Bearer)──▶ │  Auth ─▶ Route ─▶ Proxy ─▶ Audit           │
                          │                                              │
                          └────┬──────────┬──────────┬──────────┬───────┘
                               │          │          │          │
                               ▼          ▼          ▼          ▼
                          OCI MCP     Remote MCP   External    In-Process
                          (stdio)     (HTTP+OAuth)  Servers     Servers
                                                   (stdio)
```

### Backend Transport Types

| Transport | Use Case | Connection |
|-----------|----------|------------|
| `stdio` | Local MCP servers | Spawns subprocess |
| `streamable_http` | Remote MCP servers | HTTP client |
| `in_process` | Same-process servers | Direct Python import |

### Backend Authentication Methods

| Method | Use Case | Config |
|--------|----------|--------|
| `oci_config` | Local development | `~/.oci/config` file |
| `resource_principal` | OKE / Functions | Auto-detected from environment |
| `instance_principal` | OCI Compute instances | Auto-detected from environment |
| `bearer_token` | Remote MCP servers | Token in config |
| `api_key` | OCI API key auth | API key in config |
| `none` | No auth needed | - |

### Auto-Discovery

The gateway can discover MCP servers from external projects and directories:

```bash
# Scan directories for MCP servers (prints JSON, does not start)
oci-mcp-gateway --scan ~/projects --discover-only

# Discovered backends are disabled by default for operator review
# Enable them in gateway.json or via backends.d/ drop-in configs
```

Discovery checks for:
1. **`.mcp.json` / `mcp.json`** - Standard MCP client config (authoritative)
2. **`pyproject.toml`** - Projects with MCP-related entry points
3. **`server.py` / `main.py` / `app.py`** - Python files with FastMCP patterns
4. **`src/` layout** - Packages with `server.py` inside `src/<pkg>/`

External project backends support:
- **`venv`** - Path to virtual environment (gateway uses its Python binary)
- **`pythonpath`** - Additional PYTHONPATH entries for the backend process
- **`cwd`** - Working directory for the backend subprocess
- **`tags`** - Categorization labels (e.g. `auto-discovered`, `project:name`)

### Gateway Configuration

See [`gateway.example.json`](gateway.example.json) for a complete configuration example.

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

### Database Domain
| Tool | Description |
|------|-------------|
| `oci_database_*` | Database management and backup tools |

### Network Domain
| Tool | Description |
|------|-------------|
| `oci_network_*` | VCN, subnet, and security list tools |

### Observability Domain
| Tool | Description |
|------|-------------|
| `oci_observability_get_metrics` | Query OCI Monitoring metrics |
| `oci_observability_get_logs` | Query Logging Analytics |
| `oci_observability_list_alarms` | List monitoring alarms |

### Security Domain
| Tool | Description |
|------|-------------|
| `oci_security_*` | Security policies and IAM tools |

### Skills (Workflows)
| Skill | Description |
|-------|-------------|
| `oci_skill_troubleshoot_instance` | Comprehensive instance troubleshooting |
| `oci_skill_troubleshoot_database` | Database issue diagnosis |

### Gateway Management Tools
| Tool | Description |
|------|-------------|
| `gateway_health` | Gateway and backend health status |
| `gateway_list_backends` | List all backends with status |
| `gateway_audit_log` | Recent tool invocation audit log |

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

## Environment Variables

### OCI MCP Server

| Variable | Default | Description |
|----------|---------|-------------|
| `OCI_CONFIG_FILE` | `~/.oci/config` | Path to OCI config file |
| `OCI_CLI_PROFILE` | `DEFAULT` | OCI config profile name |
| `OCI_REGION` | From config | Override region |
| `OCI_TENANCY_OCID` | From config | Override tenancy |
| `COMPARTMENT_OCID` | - | Default compartment |
| `ALLOW_MUTATIONS` | `false` | Enable write operations |
| `OCI_MCP_TRANSPORT` | `stdio` | Transport: `stdio` or `streamable_http` |
| `OCI_MCP_PORT` | `8000` | HTTP port (if using `streamable_http`) |
| `OCI_MCP_LOG_LEVEL` | `INFO` | Logging level |
| `REDIS_URL` | - | Redis URL for caching (fallback: in-memory) |

### MCP Gateway

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

### Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `OCI_APM_ENDPOINT` | - | OCI APM data upload endpoint |
| `OCI_APM_PRIVATE_DATA_KEY` | - | APM private data key |
| `OCI_APM_DOMAIN_ID` | - | APM domain OCID |
| `OCI_LOGGING_ENABLED` | `false` | Enable OCI Logging integration |
| `OCI_LOGGING_LOG_ID` | - | Log OCID for ingestion |
| `OCI_LOGAN_NAMESPACE` | - | Log Analytics namespace |

## Deployment on OCI

### Container Images

```bash
# Build MCP Server image
docker build --target server -t oci-mcp-server .

# Build MCP Gateway image
docker build --target gateway -t oci-mcp-gateway .

# Push to OCI Container Registry (OCIR)
docker tag oci-mcp-server ${OCIR_REGION}.ocir.io/${OCIR_NAMESPACE}/oci-mcp-server:latest
docker push ${OCIR_REGION}.ocir.io/${OCIR_NAMESPACE}/oci-mcp-server:latest
```

### Deploy on OKE (Kubernetes)

```bash
# Apply all Kubernetes manifests
kubectl apply -k deploy/k8s/

# Verify
kubectl get pods -n mcp
kubectl get svc -n mcp
```

### Hosting Options

| Platform | Use Case | Guide |
|----------|----------|-------|
| **OKE** | Production, multi-server, gateway | [Deployment Guide](docs/deployment-guide.md) |
| **OCI Data Science** | ML teams, notebook workflows | [Deployment Guide](docs/deployment-guide.md#deployment-option-2-oci-data-science) |
| **Container Instances** | Simple, single server | [Deployment Guide](docs/deployment-guide.md#deployment-option-3-oci-container-instances) |
| **OCI Functions** | Serverless, event-driven | [Deployment Guide](docs/deployment-guide.md#deployment-option-4-oci-functions-serverless) |

### External LLM Access

| Client | Connection Method |
|--------|------------------|
| Claude Desktop / Cline | Streamable HTTP + Bearer token |
| ChatGPT (Actions) | REST adapter + OAuth 2.0 |
| Google Gemini | Function calling + HTTP proxy |
| OCI AI Agents | Private VCN + resource principal |

See the [Knowledge Base](docs/oci-mcp-knowledge-base.md) for detailed integration guides.

## Development

### Running Tests

```bash
# Unit tests
uv run pytest tests/

# Unit tests with coverage
uv run pytest tests/ --ignore=tests/integration --cov=src/mcp_server_oci --cov-report=term-missing

# Smoke test
uv run python tests/smoke_test.py
```

### Code Quality

```bash
# Linting
uv run ruff check src/

# Type checking
uv run mypy src/
```

### Adding a New Tool Domain

1. Create directory structure:
   ```
   src/mcp_server_oci/tools/newdomain/
   ├── __init__.py
   ├── SKILL.md        # Domain documentation
   ├── models.py       # Pydantic input models
   ├── tools.py        # @mcp.tool implementations
   └── formatters.py   # Markdown/JSON formatters
   ```

2. Register in `server.py`:
   ```python
   from mcp_server_oci.tools.newdomain.tools import register_newdomain_tools
   register_newdomain_tools(mcp)
   ```

### CI/CD

The project uses GitHub Actions for continuous integration:

| Workflow | Trigger | Description |
|----------|---------|-------------|
| **CI** | Push/PR to main | Lint (ruff), type check (mypy), unit tests with coverage across Python 3.12/3.13 on Linux, macOS, Windows |
| **Integration** | Manual / `integration-*` tags | Integration tests against live OCI resources (requires secrets) |
| **Secret Scan** | Push/PR | Gitleaks secret scanning with SARIF upload to GitHub Security |

## Security

- **No hardcoded credentials** - All sensitive data via environment variables
- **Config file isolation** - Uses OCI SDK standard config locations
- **Mutation protection** - Write operations disabled by default (`ALLOW_MUTATIONS=false`)
- **Input validation** - Pydantic v2 models with strict validation
- **OAuth 2.1 authentication** - JWT verification for gateway clients
- **Per-tool access control** - Scope-based authorization in the gateway
- **Secret scanning** - Gitleaks CI pipeline with vendor allowlist

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read the [CONTRIBUTING](CONTRIBUTING.md) guide first.

## Related Resources

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [OCI SDK for Python](https://docs.oracle.com/en-us/iaas/tools/python/latest/)
