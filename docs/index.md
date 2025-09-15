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

See SERVERS.md in this folder for a full list of servers.
