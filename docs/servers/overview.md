# MCP-OCI Servers Overview

This summary links to the active MCP server guides and highlights a representative tool for each service. All tool identifiers follow the `oci:<service>:<action>` naming convention with matching snake_case aliases.

| Server | Representative tool | Description |
|--------|---------------------|-------------|
| Compute | `oci:compute:list-instances` | Enumerate compute instances with lifecycle, shape, and IP metadata |
| Database | `oci:database:list-autonomous-databases` | Discover Autonomous Databases across compartments |
| Networking | `oci:network:list-vcns` | List VCNs with CIDR and DNS metadata |
| Block Storage | `oci:blockstorage:list-volumes` | Inventory block volumes with size/lifecycle state |
| Load Balancer | `oci:loadbalancer:list-load-balancers` | Inspect load balancers and listener state |
| Security | `oci:security:list-iam-users` | Enumerate IAM users with lifecycle and MFA hints |
| Cost / FinOpsAI | `oci:cost:get-summary` | Aggregated Usage API cost summary with currency detection |
| Inventory | `oci:inventory:list-resources` | Cross-service resource catalogue with tag filters |
| Log Analytics | `oci:loganalytics:execute-query` | Run Logging Analytics queries with namespace auto-detection |
| Observability Hub | `oci:observability:get-observability-metrics-summary` | Correlate tracing, metrics, and recent MCP calls |
| Generative AI Agents | `oci:agents:list-agents` | List Generative AI agents or proxies |

## Operational Tips

- Reuse cached lookups: shared cache helpers store list results and name→OCID mappings (`MCP_CACHE_TTL_*`).
- Privacy masking is enabled by default; disable only for debugging (`MCP_OCI_PRIVACY=false`).
- Most list tools accept pagination (`limit`, `page`) and region overrides. Use `force_refresh=true` to bypass caches when troubleshooting.
- Combine stdio transport for CLI usage and `streamable-http` or `sse` for long-running operations with progress updates.
- Observability helpers live in `oci-mcp-observability` and expose recent call traces, OTEL configuration, and namespace utilities.
