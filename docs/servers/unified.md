# OCI Unified MCP Server (`oci-mcp-unified`)

## Overview
- Purpose: Single server exposing tools from all `mcp_servers/*` packages plus high-level skills (`mcp_servers/skills/*`).
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8010` (override with `METRICS_PORT`)

## Tools
The unified server dynamically aggregates tools from:
- Core services: compute, db, network, security, cost, inventory, blockstorage, loadbalancer, loganalytics, objectstorage
- Skills layer: cost analysis, inventory audit, network diagnostics, compute management, security posture

Use `server://manifest` to list the loaded tools at runtime.

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh unified`
- Docker helper: `scripts/docker/run-server.sh unified`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Transport:
  - `MCP_TRANSPORT=stdio|http|sse|streamable-http`
  - `MCP_HOST` and `MCP_PORT` for network transports

