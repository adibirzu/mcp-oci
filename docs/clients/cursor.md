# Cursor Integration

Cursor supports MCP servers via its Settings UI. Add entries with a command and args.

Steps
- Open Cursor Settings → MCP Servers (or search "MCP").
- Add a new server with a name and command.

Examples

Standard MCP servers:
- IAM (local):
  - Command: `mcp-oci-serve-iam`
  - Args: `--profile DEFAULT --region eu-frankfurt-1`
- Usage API (local):
  - Command: `mcp-oci-serve-usageapi`
  - Args: `--profile DEFAULT --region eu-frankfurt-1`
- Compute (local):
  - Command: `mcp-oci-serve-compute`
  - Args: `--profile DEFAULT --region eu-frankfurt-1`

FastMCP servers (recommended for better performance):
- IAM FastMCP:
  - Command: `mcp-oci-serve-fast`
  - Args: `iam --profile DEFAULT --region eu-frankfurt-1`
- Compute FastMCP:
  - Command: `mcp-oci-serve-fast`
  - Args: `compute --profile DEFAULT --region eu-frankfurt-1`
- Usage API FastMCP:
  - Command: `mcp-oci-serve-fast`
  - Args: `usageapi --profile DEFAULT --region eu-frankfurt-1`

Docker alternative:
- Command: `docker`
- Args: `run --rm -i -v ${HOME}/.oci:/root/.oci mcp-oci mcp-oci-serve iam --profile DEFAULT --region eu-frankfurt-1`

Notes
- Ensure your `~/.oci/config` is readable by Cursor environment.
- Use `--require-confirm` for mutating tools to add safety.
- Use `mcp-oci-serve <service>` for any other service; see docs/SERVERS.md.
