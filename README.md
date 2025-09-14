# MCP OCI Servers

## Overview
A collection of Model Context Protocol (MCP) servers for Oracle Cloud Infrastructure (OCI), following the AWS MCP design guidelines and documentation style. All servers are Python-based and use the OCI Python SDK. Initial focus is on OCI Services API tools; Observability will be added next.

- Design reference: https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md
- Docs structure: https://github.com/awslabs/mcp/tree/main/docusaurus
- Server layout mirrors AWS MCP servers under `src/`.

## Installation
- With Makefile
```
make setup
```
- Manual
```
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
```

## Configuration
Use the OCI SDK via `~/.oci/config` profiles or environment variables.
- Common env: `OCI_TENANCY`, `OCI_USER`, `OCI_REGION`, `OCI_KEY_FINGERPRINT`, `OCI_PRIVATE_KEY_PATH`, `OCI_PASS_PHRASE`.

## Tools / Resources
Tools are named `oci:<service>:<action>` (e.g., `oci:iam:list-users`) and are deterministic/idempotent where possible. Pagination and long-running operations return structured outputs and continuation tokens.

## Usage
Each server is published under `src/mcp_oci_<service>/`. You can serve a service over stdio for MCP hosts:
- Generic: `mcp-oci-serve iam` (or any service name)
- Convenience (IAM): `mcp-oci-serve-iam`
Wire the exported tools (see `register_tools()` in each `server.py`) into your MCP runtime/host if managing integration manually.
- Example servers with initial tools:
  - `mcp_oci_iam` — `oci:iam:list-users`
  - `mcp_oci_compute` — `oci:compute:list-instances`
  - `mcp_oci_objectstorage` — `oci:objectstorage:list-buckets`

## Development
- `make dev` — run local dev server if `dev/mcp-oci-x-server/` exists; otherwise prints a hint.
- `make test` — run pytest with coverage.
- `make lint` / `make fmt` — Ruff/Black; MyPy for type checks.

## Next: mcp-oci-servers
See the index of all servers in `docs/SERVERS.md`.
