# MCP Server Architecture (OCI)

This repo implements a consistent MCP server pattern across OCI services.

Core runtime
- Transport: JSON-RPC over stdio (Content-Length framing) in `mcp_oci_runtime/stdio.py`.
- Methods implemented: `initialize`, `tools/list`, `tools/call`, `shutdown`.
- Safety: confirmation gate for mutating tools (`--require-confirm` or `confirm=true`), default profile/region injection, stderr logging.

Server modules
- One package per service under `src/mcp_oci_<service>/` with:
  - `server.py` exporting `register_tools()` and optional `create_client()`.
  - `__main__.py` calling `run_with_tools(register_tools())` for stdio.
  - `README.md` with Overview/Tools/Usage.
- Common auth/client factory: `mcp_oci_common.make_client` and `get_config`.

Tool shape
- Each tool spec includes:
  - `name`: `oci:<service>:<action>` (stable identifier)
  - `description`: clear, concise
  - `parameters`: JSON Schema (type=object, properties, required)
  - `handler`: callable (keyword args match schema)
  - `mutating` (optional): true for actions that change state

Naming & files
- Packages: `mcp_oci_<service>` (e.g., `mcp_oci_iam`)
- Tools: `oci:<service>:<action>` (e.g., `oci:iam:list-users`)
- README per server follows MCP best practices and OCI service patterns.

Entry points
- Generic: `mcp-oci-serve <service>`
- Convenience: `mcp-oci-serve-<service>` (e.g., `mcp-oci-serve-iam`)

Testing
- Minimal integration tests under `tests/integration/` with direct OCI calls.
- Auto-discovery when possible; configurable via environment variables.

Extensibility
- Introspection server (`mcp_oci_introspect`) lists SDK methods to help track new features.
- Monitoring namespace discovery prefers direct SDK methods when available.

Response and error conventions
- Handlers attach `opc_request_id` when available (from SDK response headers)
- Error responses include `service_code` and `opc_request_id` (when provided by the SDK)
