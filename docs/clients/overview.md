# MCP Clients Overview

These servers speak MCP over stdio and work with common MCP-enabled clients, including Claude Desktop, Cursor, and Cline (VS Code).

General requirements
- Ensure `mcp-oci` CLI is on PATH (installed in your Python venv or system).
- Provide OCI credentials via `~/.oci/config` and set a profile/region.
- Prefer Frankfurt in examples: `--region eu-frankfurt-1`.
- Use `mcp-oci doctor` to verify before wiring clients.
 - GUI clients may not inherit your shell PATH; use absolute paths to the venv bin if needed (see Claude Desktop docs). macOS logs: `~/Library/Logs/Claude/`.

Common server commands
- Generic: `mcp-oci-serve <service> --profile DEFAULT --region eu-frankfurt-1`
- Convenience: `mcp-oci-serve-iam` (and others listed in pyproject scripts)
- Docker: `docker run --rm -it -v $HOME/.oci:/root/.oci mcp-oci mcp-oci-serve iam --profile DEFAULT --region eu-frankfurt-1`

Core servers to add first
- IAM, Compute, Object Storage, Usage API, Monitoring, Log Analytics, Introspect
