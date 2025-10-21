# MCP OCI Documentation

This documentation follows MCP best practices and FastMCP framework guidelines. See MCP protocol at https://modelcontextprotocol.io/ and FastMCP at https://gofastmcp.com/.

Workflow at a glance
- Install and verify: `make setup && mcp-oci doctor --profile DEFAULT --region us-phoenix-1`
- Serve a service: `mcp-oci-serve iam --profile DEFAULT --region us-phoenix-1`
- Call a tool: `mcp-oci call iam oci:iam:list-users --params '{"compartment_id":"ocid1.tenancy..."}'`
- Mutating actions: use `dry_run=true` then `confirm=true`, or serve with `--require-confirm`.
- Cost analytics: see `servers/usageapi` and `integrations` for showusage/showoci.

Sections
- Servers (OCI services under `src/`)
- Development (build, test, lint, fmt, vendor examples)
- Security and Configuration
- How-To guides (e.g., cost analysis)
- Troubleshooting (common errors and client-specific guides)

## Performance and resiliency tunables

Client reuse and resilient I/O are enabled by default. You can adjust behavior using environment variables:

General OCI SDK (shared client factory)
- OCI_ENABLE_RETRIES=true|false (default true) — enable OCI SDK retry strategy when supported
- OCI_REQUEST_TIMEOUT=seconds — set both connect/read timeouts
- OCI_REQUEST_TIMEOUT_CONNECT=seconds, OCI_REQUEST_TIMEOUT_READ=seconds — fine‑grained timeouts

Caching (shared disk+memory cache)
- MCP_CACHE_DIR=/tmp/mcp-oci-cache (default)
- MCP_CACHE_TTL=3600 — default TTL seconds for cache entries

Log Analytics REST (oci-mcp-loganalytics)
- LA_HTTP_POOL=16 — HTTP connection pool size
- LA_HTTP_RETRIES=3 — automatic retries on 429/5xx
- LA_HTTP_BACKOFF=0.2 — per‑request backoff factor
- LA_HTTP_TIMEOUT=60 — per‑request timeout seconds

Networking REST (create_vcn_with_subnets_rest)
- NET_HTTP_POOL=16 — HTTP connection pool size
- NET_HTTP_RETRIES=3 — automatic retries on 429/5xx
- NET_HTTP_BACKOFF=0.2 — per‑request backoff factor

Notes
- SDK clients are reused per (client class, profile, region) to minimize cold‑start/TLS overhead.
- Defaults are production‑safe; increase *_HTTP_POOL for higher concurrency workloads.

See SERVERS.md in this folder for a full list of servers.
