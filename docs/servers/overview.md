# Servers Overview & Quick Start Tools

This page highlights commonly used servers and a starter tool for each.

IAM
- Tool: `oci:iam:list-users`
- Example: `mcp-oci call iam oci:iam:list-users --params '{"compartment_id":"ocid1.tenancy..."}'`

Compute
- Tool: `oci:compute:list-instances`
- Example: `mcp-oci call compute oci:compute:list-instances --params '{"compartment_id":"ocid1.compartment..."}'`

Object Storage
- Tool: `oci:objectstorage:list-buckets`
- Example: `mcp-oci call objectstorage oci:objectstorage:list-buckets --params '{"namespace_name":"axxx","compartment_id":"ocid1.compartment..."}'`

Monitoring
- Tool: `oci:monitoring:summarize-metrics`
- Example: `mcp-oci call monitoring oci:monitoring:summarize-metrics --params '{"compartment_id":"ocid1.compartment...","namespace":"oci_computeagent","query":"CpuUtilization[1m].mean()","start_time":"2025-01-01T00:00:00Z","end_time":"2025-01-01T01:00:00Z"}'`

Performance and Token Optimization
- Server-side caching (in-memory + on-disk via MCPCache) reduces repeated API calls for frequently used list operations.
- Name→OCID registry is updated automatically when listing compartments, VCNs, subnets, and instances, allowing future calls to resolve names without extra requests.
- You can reference resources by human-readable names (e.g., `compartment_name` in compute) and the server maps them to OCIDs from the registry.
- Introspection tools: `mcp:registry:dump` and `mcp:registry:resolve` let you inspect and use the in-process registry without additional API calls.
- Observability helpers: `oci:observability:get-recent-calls` shows recent MCP call paths and queries to spot missing capabilities.

Cache TTL tuning
- Global default TTL: `MCP_CACHE_TTL` (seconds, default 3600).
- Service-specific TTLs override the default when present:
  - `MCP_CACHE_TTL_COMPUTE`, `MCP_CACHE_TTL_NETWORKING`, `MCP_CACHE_TTL_IAM`, `MCP_CACHE_TTL_OKE`, `MCP_CACHE_TTL_FUNCTIONS`, `MCP_CACHE_TTL_STREAMING`.

Usage API
- Tool: `oci:usageapi:cost-by-service`
- Example: `mcp-oci call usageapi oci:usageapi:cost-by-service --params '{"tenant_id":"ocid1.tenancy...","days":7}'`
