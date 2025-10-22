# MCP-OCI Documentation Hub

This documentation follows the OCI MCP design guidelines (deterministic tools, structured errors, least-privilege defaults, explicit confirmation for destructive workflows). Familiarity with the [Model Context Protocol](https://modelcontextprotocol.io/) and [FastMCP](https://gofastmcp.com/) is recommended.

## Quick workflow

1. `make setup` – create virtualenv and install `.[dev]`
2. `mcp-oci doctor --profile DEFAULT --region us-phoenix-1` – verify credentials
3. `scripts/mcp-launchers/start-mcp-server.sh compute --daemon` – start a server
4. `mcp-oci-serve compute --transport stdio` – expose a single service
5. `scripts/docker/run-server.sh compute` – run the same server inside Docker

## Documentation map

- **Server guides**: see the files under [docs/servers](servers) for per-service tools, environment variables, and runbooks.
- **Deployment**: scripts under `ops/` cover Docker Compose, OKE manifests, and observability bootstrap.
- **Common utilities**: shared client, cache, observability, and privacy layers live in [`mcp_oci_common`](../mcp_oci_common).
- **Development**: the Makefile targets `fmt`, `lint`, `test`, and `dev` streamline local iteration.

## Performance & resiliency tuning

- `OCI_ENABLE_RETRIES=true|false` – toggle OCI SDK retry strategy (default `true`).
- `OCI_REQUEST_TIMEOUT_CONNECT` / `OCI_REQUEST_TIMEOUT_READ` – fine-grained timeouts (seconds).
- `MCP_CACHE_TTL_{SERVICE}` – override cache TTL for a specific server (default `3600`).
- `NET_HTTP_*` / `LA_HTTP_*` – size/retry tuning for Networking REST and Logging Analytics clients.

All servers reuse SDK clients per `(client class, profile, region)` to minimise TLS handshakes. When optional dependencies (Pyroscope, FastAPI instrumentation) are unavailable, servers degrade gracefully without affecting tool execution.

## Testing strategy

- **Unit**: faked OCI responses ensure tools return deterministic payloads without hitting live services.
- **Integration**: optional scripts under `scripts/test_*` exercise live tenancy endpoints when credentials are available.
- **Observability smoke**: `python test_observability_e2e.py` validates the OTLP pipeline and dashboards.

Always run `make fmt lint test` before raising a PR.
