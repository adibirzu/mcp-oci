# MCP OCI Servers

## Overview
A collection of Model Context Protocol (MCP) servers for Oracle Cloud Infrastructure (OCI), following the AWS MCP design guidelines and documentation style. All servers are Python-based and use the OCI Python SDK. Initial focus is on OCI Services API tools; Observability and Cost Analytics are included.

- Design reference: https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md
- Docs structure: https://github.com/awslabs/mcp/tree/main/docusaurus
- Server layout mirrors AWS MCP servers under `src/`.

## Quickstart
- Install (with Makefile)
```
make setup
```
- Verify connectivity
```
mcp-oci doctor --profile DEFAULT --region eu-frankfurt-1
```
- Manual install
```
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
```

## Configuration
Use the OCI SDK via `~/.oci/config` profiles or environment variables.
- Common env: `OCI_TENANCY`, `OCI_USER`, `OCI_REGION`, `OCI_KEY_FINGERPRINT`, `OCI_PRIVATE_KEY_PATH`, `OCI_PASS_PHRASE`.

## Tools / Resources
Tools are named `oci:<service>:<action>` (e.g., `oci:iam:list-users`). Read/list tools are prioritized; mutating tools require confirmation. Pagination and long-running operations return structured outputs and continuation tokens.

Mutating tools and safety
- The stdio runtime supports `--require-confirm` or per-call `confirm=true`.
- Many mutating tools also support `dry_run=true` to preview the request.

## Usage
Each server is published under `src/mcp_oci_<service>/`. Serve a service over stdio for MCP hosts:
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
- `make vendor-examples` — vendor Oracle example tools (showusage/showoci) under `third_party/` (set `ORACLE_SDK_PATH`).
- `make doctor` — verify OCI config and connectivity with the SDK.

Integration testing
- `make test-integration` — runs direct OCI integration tests; requires env vars. Use `make integration-env` to see examples.

Workflow checklist
1) Install dependencies and verify: `make setup && make doctor`
2) Run a server locally: `mcp-oci-serve iam --profile DEFAULT --region eu-frankfurt-1`
3) Call a tool: `mcp-oci call iam oci:iam:list-users --params '{"compartment_id":"ocid1.tenancy..."}'`
4) For cost analytics, serve Usage API and run summarized usage; optionally integrate showusage/showoci (see docs/integrations.md)
5) For mutating actions, test with `dry_run=true`, then re-run with `confirm=true` or serve with `--require-confirm`.

## Next: mcp-oci-servers
See the index of all servers in `docs/SERVERS.md`.

## Docker
Build and run an MCP server in Docker:
```
docker build -t mcp-oci .
docker run --rm -it -v $HOME/.oci:/root/.oci mcp-oci mcp-oci-serve iam --profile DEFAULT --region eu-frankfurt-1
```
Replace the serve command to run other services (e.g., `mcp-oci-serve-usageapi`). Ensure your OCI config is mounted into the container.

Docker Compose (optional)
```
version: "3.8"
services:
  mcp_oci:
    build: .
    command: ["mcp-oci-serve", "iam", "--profile", "DEFAULT", "--region", "us-phoenix-1", "--log-level", "INFO"]
    volumes:
      - ${HOME}/.oci:/root/.oci:ro
```
