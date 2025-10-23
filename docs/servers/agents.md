# OCI Generative AI Agents MCP Server (`oci-mcp-agents`)

## Overview
- Purpose: OCI Generative AI agent lifecycle and endpoint helpers.
- Default transport: stdio (set `MCP_TRANSPORT=http|sse|streamable-http` as needed)
- Default metrics port: `8011` (override with `METRICS_PORT`)

## Tools
| Tool | Description |
|------|-------------|
| `create_agent` | Create a Generative AI Agent (OCI/proxy) |
| `create_agent_endpoint` | Create an Agent Endpoint (OCI mode) |
| `create_knowledge_base` | Create a Knowledge Base (OCI mode) |
| `delete_agent` | Delete agent by id |
| `delete_agent_endpoint` | Delete Agent Endpoint (OCI mode) |
| `delete_knowledge_base` | Delete Knowledge Base (OCI mode) |
| `doctor` | Return server health, config summary, and masking status |
| `get_agent` | Get agent details by id |
| `get_agent_endpoint` | Get Agent Endpoint by OCID (OCI mode) |
| `get_knowledge_base` | Get Knowledge Base by OCID (OCI mode) |
| `healthcheck` | Liveness check for agents server |
| `list_agent_endpoints` | List Agent Endpoints in a compartment (OCI mode) |
| `list_agents` | List Generative AI Agents (OCI/proxy) |
| `list_knowledge_bases` | List Knowledge Bases in a compartment (OCI mode) |
| `test_agent_message` | Send a test message to an agent and get reply |
| `update_agent` | Update agent fields (name/type/model/description/config) |
| `update_agent_endpoint` | Update Agent Endpoint fields (OCI mode) |
| `update_knowledge_base` | Update Knowledge Base fields (OCI mode) |

## Running
- Local launcher: `scripts/mcp-launchers/start-mcp-server.sh agents`
- CLI entrypoint: `mcp-oci-serve agents`
- Docker helper: `scripts/docker/run-server.sh agents`
- Stop daemonised instance: `scripts/mcp-launchers/start-mcp-server.sh stop agents`

## Configuration
- Shared credentials resolved via `mcp_oci_common.get_oci_config()`
- Respect privacy defaults (`MCP_OCI_PRIVACY=true`, disable with caution)
- Service-specific hints:
  - `GAI_ADMIN_ENDPOINT`
  - `GAI_AGENT_ENDPOINT`
  - `GAI_AGENT_API_KEY`

## Testing notes
- Unit: see `tests/unit/test_mcp_servers.py` (faked OCI responses).
- Manual: `python -m mcp_servers.agents.server` launches the FastMCP runtime.

