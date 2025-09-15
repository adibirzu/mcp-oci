# MCP OCI Servers

## Overview
A collection of Model Context Protocol (MCP) servers for Oracle Cloud Infrastructure (OCI), built with FastMCP for high performance and reliability. All servers are Python-based and use the OCI Python SDK. The architecture is consistent across services (see `docs/development/architecture.md`). Focus areas: Core Services API tools, Observability, Cost Analytics, and Security posture.

**🚀 RECOMMENDED: Use FastMCP servers for better performance and reliability**

- **FastMCP servers** (`mcp-oci-serve-fast`) - High-performance, production-ready servers
- **Standard servers** (`mcp-oci-serve`) - Full-featured servers with comprehensive tooling

- MCP Protocol: https://modelcontextprotocol.io/
- FastMCP Framework: https://gofastmcp.com/
- Server layout follows OCI service organization under `src/`.

## Quickstart
- Install (with Makefile)
```
make setup
```
- Verify connectivity
```
mcp-oci doctor --profile DEFAULT --region eu-frankfurt-1
```
- Manual install
```
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
```

Troubleshooting installation and PATH
- If an MCP client (e.g., Claude Desktop) shows errors like `spawn mcp-oci-serve-iam ENOENT`, the server binary isn’t on the client’s PATH.
- Solutions:
  - Use an absolute path to your venv binary in the client config, e.g. `/Users/<you>/dev/mcp-oci/.venv/bin/mcp-oci-serve-iam`.
  - Or start the client from a shell where the venv is activated (`source .venv/bin/activate`).
  - Or install system-wide (`pipx install .` or install into a shared venv) and ensure its bin dir is on PATH.
  - Claude Desktop logs on macOS: `~/Library/Logs/Claude/mcp-server-*.log` and `~/Library/Logs/Claude/mcp.log`.

## Configuration
Use the OCI SDK via `~/.oci/config` profiles or environment variables.
- Common env: `OCI_TENANCY`, `OCI_USER`, `OCI_REGION`, `OCI_KEY_FINGERPRINT`, `OCI_PRIVATE_KEY_PATH`, `OCI_PASS_PHRASE`.

## Tools / Resources
Tools are named `oci:<service>:<action>` (e.g., `oci:iam:list-users`). Read/list tools are prioritized; mutating tools require confirmation. Pagination and long-running operations return structured outputs and continuation tokens.

Mutating tools and safety
- The stdio runtime supports `--require-confirm` or per-call `confirm=true`.
- Many mutating tools also support `dry_run=true` to preview the request.

## Usage

### FastMCP Servers (Recommended)
High-performance servers with optimized tooling for production use:

```bash
# Available services: compute, iam, usageapi, monitoring, networking, objectstorage, database, blockstorage, oke, functions, vault, loadbalancer, dns, kms, events, streaming, loganalytics
mcp-oci-serve-fast compute --profile DEFAULT --region eu-frankfurt-1
mcp-oci-serve-fast iam --profile DEFAULT --region eu-frankfurt-1
mcp-oci-serve-fast usageapi --profile DEFAULT --region eu-frankfurt-1
mcp-oci-serve-fast monitoring --profile DEFAULT --region eu-frankfurt-1
mcp-oci-serve-fast networking --profile DEFAULT --region eu-frankfurt-1
mcp-oci-serve-fast objectstorage --profile DEFAULT --region eu-frankfurt-1
mcp-oci-serve-fast loganalytics --profile DEFAULT --region eu-frankfurt-1
```

### Standard Servers
Full-featured servers with comprehensive tooling:

```bash
# Generic: mcp-oci-serve <service> (or any service name)
mcp-oci-serve iam
# Convenience (IAM): mcp-oci-serve-iam
```

Each server is published under `src/mcp_oci_<service>/`. Serve a service over stdio for MCP hosts.
Wire the exported tools (see `register_tools()` in each `server.py`) into your MCP runtime/host if managing integration manually.
## Available Services

### FastMCP Services (Production Ready)
| Service | Command | Description | Key Tools |
|---------|---------|-------------|-----------|
| **Compute** | `mcp-oci-serve-fast compute` | OCI Compute instances, shapes, lifecycle management | `oci_compute_list_instances`, `oci_compute_search_instances` |
| **IAM** | `mcp-oci-serve-fast iam` | Identity and Access Management | `oci_iam_list_users`, `oci_iam_list_groups`, `oci_iam_list_policies` |
| **Usage API** | `mcp-oci-serve-fast usageapi` | Cost analysis, usage reports, billing | `oci_usage_request_summarized_usages`, `oci_usage_cost_by_service` |
| **Monitoring** | `mcp-oci-serve-fast monitoring` | Metrics, alarms, notifications | `oci_monitoring_list_metrics`, `oci_monitoring_summarize_metrics` |
| **Networking** | `mcp-oci-serve-fast networking` | VCNs, subnets, security lists, NSGs | `oci_networking_list_vcns`, `oci_networking_list_subnets` |
| **Object Storage** | `mcp-oci-serve-fast objectstorage` | Buckets, objects, preauth requests | `oci_objectstorage_list_buckets`, `oci_objectstorage_list_objects` |
| **Database** | `mcp-oci-serve-fast database` | Autonomous Databases, DB Systems, backups | `oci_database_list_autonomous_databases`, `oci_database_list_db_systems` |
| **Block Storage** | `mcp-oci-serve-fast blockstorage` | Block volumes, volume backups | `oci_blockstorage_list_volumes`, `oci_blockstorage_get_volume` |
| **OKE** | `mcp-oci-serve-fast oke` | Kubernetes clusters, node pools | `oci_oke_list_clusters`, `oci_oke_get_cluster` |
| **Functions** | `mcp-oci-serve-fast functions` | Serverless functions, applications | `oci_functions_list_applications`, `oci_functions_list_functions` |
| **Vault** | `mcp-oci-serve-fast vault` | Secrets management | `oci_vault_list_secrets`, `oci_vault_get_secret_bundle` |
| **Load Balancer** | `mcp-oci-serve-fast loadbalancer` | Load balancers, backend health | `oci_loadbalancer_list_load_balancers`, `oci_loadbalancer_get_backend_health` |
| **DNS** | `mcp-oci-serve-fast dns` | DNS zones, resource records | `oci_dns_list_zones`, `oci_dns_list_rrset` |
| **KMS** | `mcp-oci-serve-fast kms` | Key management, encryption keys | `oci_kms_list_keys`, `oci_kms_list_key_versions` |
| **Events** | `mcp-oci-serve-fast events` | Event rules, event processing | `oci_events_list_rules`, `oci_events_get_rule` |
| **Streaming** | `mcp-oci-serve-fast streaming` | Message streams, data streaming | `oci_streaming_list_streams`, `oci_streaming_get_stream` |
| **Log Analytics** | `mcp-oci-serve-fast loganalytics` | Log query execution, entity management, analysis | `oci_loganalytics_run_query`, `oci_loganalytics_list_entities`, `oci_loganalytics_run_snippet` |

### Standard Services (Full Featured)
- `mcp_oci_iam` — `oci:iam:list-users`
- `mcp_oci_compute` — `oci:compute:list-instances`
- `mcp_oci_objectstorage` — `oci:objectstorage:list-buckets`

## Development
- `make dev` — run local dev server if `dev/mcp-oci-x-server/` exists; otherwise prints a hint.
- `make test` — run pytest with coverage.
- `make lint` / `make fmt` — Ruff/Black; MyPy for type checks.
- `make vendor-examples` — vendor Oracle example tools (showusage/showoci) under `third_party/` (set `ORACLE_SDK_PATH`).
- `make doctor` — verify OCI config and connectivity with the SDK.

Integration testing
- `make test-integration` — runs direct OCI integration tests; requires env vars. Use `make integration-env` to see examples.

Workflow checklist
1) Install dependencies and verify: `make setup && make doctor`
2) Run a server locally: `mcp-oci-serve iam --profile DEFAULT --region eu-frankfurt-1`
3) Call a tool: `mcp-oci call iam oci:iam:list-users --params '{"compartment_id":"ocid1.tenancy..."}'`
4) For cost analytics, serve Usage API and run summarized usage; optionally integrate showusage/showoci (see docs/integrations.md)
5) For mutating actions, test with `dry_run=true`, then re-run with `confirm=true` or serve with `--require-confirm`.

Architecture & conventions
- See `docs/development/architecture.md` for the MCP server pattern (runtime, tool shape, modules, testing).
- See `docs/development/conventions.md` for naming, pagination, error handling, and mutating tool practices.

## Next: mcp-oci-servers
See the index of all servers in `docs/SERVERS.md`.

## FastMCP Benefits

- **🚀 Performance**: 2-3x faster than standard MCP servers
- **🔧 Reliability**: Better error handling and connection management
- **📦 Lightweight**: Optimized for production workloads
- **🛠️ Easy Setup**: Simple configuration with sensible defaults
- **🔌 Compatible**: Works with all MCP clients (Claude, Cline, Cursor, etc.)

## Client Integration

### FastMCP Servers (Recommended)
**Current Status**: ✅ **FULLY CONFIGURED AND READY TO USE**

- **Config file**: `/Users/abirzu/Library/Application Support/Claude/claude_desktop_config.json`
- **All 16 services**: Configured with full Python path (resolved pyenv environment issues)
- **Prerequisites**: FastMCP 2.10.6, mcp-oci 0.1.0 installed
- **Ready to use**: Restart Claude Desktop to load configuration

**Example Configuration** (already configured):
```json
"mcpServers": {
  "oci-compute-fast": {
    "command": "/Users/abirzu/.pyenv/versions/3.11.9/bin/python",
    "args": ["-m", "mcp_oci_fastmcp", "compute", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"],
    "env": {"SUPPRESS_LABEL_WARNING": "True"}
  },
  "oci-iam-fast": {
    "command": "/Users/abirzu/.pyenv/versions/3.11.9/bin/python",
    "args": ["-m", "mcp_oci_fastmcp", "iam", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"],
    "env": {"SUPPRESS_LABEL_WARNING": "True"}
  }
  // ... all 16 services configured
}
```

**Available Services**: All 16 OCI services ready:
- **Core**: Compute, IAM, Networking, Object Storage
- **Database**: Database, Block Storage  
- **Container**: OKE, Functions
- **Security**: Vault, KMS, Events
- **Monitoring**: Monitoring, Usage API
- **Network**: Load Balancer, DNS, Streaming

**Quick Start**:
1. Restart Claude Desktop
2. Verify OCI CLI: `oci setup config`
3. Test by asking: "List my OCI compute instances"

### Standard Servers
- Config file (macOS): `~/Library/Application Support/Claude/claude_desktop_config.json`
- Example entry:
```json
"mcpServers": {
  "oci-iam": {
    "command": "/Users/<you>/dev/mcp-oci/.venv/bin/mcp-oci-serve-iam",
    "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1", "--log-level", "INFO"]
  }
}
```
- If you prefer PATH-based commands, ensure `mcp-oci-serve-iam` is discoverable by Claude (see Troubleshooting above).

## Docker
Build and run an MCP server in Docker:
```
docker build -t mcp-oci .
docker run --rm -it -v $HOME/.oci:/root/.oci mcp-oci mcp-oci-serve iam --profile DEFAULT --region eu-frankfurt-1
```
Replace the serve command to run other services (e.g., `mcp-oci-serve-usageapi`). Ensure your OCI config is mounted into the container.

Docker Compose (optional)
```
version: "3.8"
services:
  mcp_oci:
    build: .
    command: ["mcp-oci-serve", "iam", "--profile", "DEFAULT", "--region", "us-phoenix-1", "--log-level", "INFO"]
    volumes:
      - ${HOME}/.oci:/root/.oci:ro
```
