# Server Name (OCI <Service>)

## Overview
Brief description of the MCP server for OCI <Service>. Implements tools following MCP best practices and FastMCP framework guidelines.

## Installation
```
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
```

## Configuration
- Uses OCI Python SDK auth via `~/.oci/config` or env vars.
- Example env: `OCI_TENANCY`, `OCI_USER`, `OCI_REGION`, `OCI_KEY_FINGERPRINT`, `OCI_PRIVATE_KEY_PATH`.

## Tools / Resources
- `oci:<service>:<action>` tools (idempotent where possible), paginated list operations, and safe defaults.

## Usage
Example MCP client config pointing to this server; commands to start the server.

## Development
- `make dev` to run locally; `make test` for pytest; `make lint fmt` before commits.

## Next: mcp-oci-servers
Link to repository index of all OCI servers.
