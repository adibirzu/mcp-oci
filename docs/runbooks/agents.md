# Agents MCP Server Runbook (oci-mcp-agents)

Use this runbook for GenAI agent lifecycle and endpoint validation.

## Inputs
- Compartment OCID or name
- Agent OCID or display name (optional)
- Endpoint OCID (optional)

## Steps
1. **List agents and endpoints**
   - Tools: `list_agents`, `list_agent_endpoints`
2. **Get agent/endpoint details**
   - Tools: `get_agent`, `get_agent_endpoint`
3. **Create or update agent resources**
   - Tools: `create_agent`, `update_agent`, `create_agent_endpoint`, `update_agent_endpoint`
4. **Knowledge base management (if required)**
   - Tools: `create_knowledge_base`, `get_knowledge_base`, `update_knowledge_base`, `list_knowledge_bases`
5. **Test agent response**
   - Tool: `test_agent_message`
6. **Cleanup if requested**
   - Tools: `delete_agent`, `delete_agent_endpoint`, `delete_knowledge_base`

## Skill/Tool mapping
- Inventory: `list_agents`, `list_agent_endpoints`, `list_knowledge_bases`
- Details: `get_agent`, `get_agent_endpoint`, `get_knowledge_base`
- Provisioning: `create_agent`, `create_agent_endpoint`, `create_knowledge_base`
- Updates: `update_agent`, `update_agent_endpoint`, `update_knowledge_base`
- Validation: `test_agent_message`
- Cleanup: `delete_agent`, `delete_agent_endpoint`, `delete_knowledge_base`

## Outputs
- Agent inventory and status
- Validation of agent responses
- Change summary for created/updated resources
