# OCI Operations Agent Reference Documentation

> **Last Updated**: December 17, 2025
> **Version**: 0.0.2
> **Test Status**: 7 MCP servers connected, 164 tools available

## Overview

The OCI Operations Agent is an autonomous AI agent for Oracle Cloud Infrastructure management and monitoring. Built with TypeScript/Node.js, it uses LangChain's ReAct pattern to intelligently execute infrastructure operations through MCP (Model Context Protocol) servers.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    OCI Operations Agent                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐      │
│  │   Slack     │    │   HTTP API   │    │   LangChain    │      │
│  │   Bot       │───▶│   Express    │───▶│   ReAct Agent  │      │
│  └─────────────┘    └──────────────┘    └───────┬────────┘      │
│                                                   │               │
│  ┌────────────────────────────────────────────────┴───────┐     │
│  │                     Tool Catalog                        │     │
│  │   Aggregates tools from all connected MCP servers       │     │
│  └──────────────────────┬─────────────────────────────────┘     │
│                          │                                        │
│  ┌───────────────────────┴────────────────────────────────┐     │
│  │                  MCP Server Registry                    │     │
│  │                                                          │     │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │     │
│  │  │ Unified │  │ Compute │  │ Network │  │  Cost   │   │     │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘   │     │
│  │       │            │            │            │         │     │
│  │  ┌────┴────┐  ┌────┴────┐  ┌────┴────┐  ┌────┴────┐   │     │
│  │  │Security │  │ Logan   │  │ Observ. │  │  More   │   │     │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │           OpenTelemetry Observability                    │     │
│  │           (OCI APM Integration)                          │     │
│  └─────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. LangChain ReAct Agent
- Uses the ReAct (Reasoning and Acting) pattern for intelligent decision-making
- Supports multiple LLM providers (Anthropic Claude, OpenAI)
- Automatically converts MCP tools to LangChain DynamicStructuredTools
- Maintains conversation history for contextual interactions

### 2. MCP Server Integration
- Connects to multiple OCI MCP servers via stdio and HTTP transports
- Auto-reconnect logic with circuit breaker pattern
- Parallel HTTP server connections, sequential stdio connections
- Real-time tool catalog refresh

### 3. Slack Bot Interface
- Socket Mode integration for secure communication
- Interactive wizards (e.g., Compute Instance Creation Wizard)
- Quick actions for common operations
- Multi-tenancy support with profile selection
- Thread-based conversation history

### 4. OpenTelemetry Observability
- Full tracing integration with OCI APM
- LLM call tracing with GenAI semantic conventions
- Agent invocation and step tracking
- MCP tool execution tracing
- Slack message handling traces

## Configured MCP Servers

| Server ID | Name | Tools | Description | Transport |
|-----------|------|-------|-------------|-----------|
| oci-mcp-unified | OCI Unified MCP Server | 65 | All OCI capabilities in one server | stdio |
| oci-mcp-compute | OCI Compute MCP Server | 9 | Instance management | stdio |
| oci-mcp-network | OCI Network MCP Server | 9 | VCN, subnets, security | stdio |
| oci-mcp-cost | OCI Cost MCP Server | 24 | Cost analysis and budgets | stdio |
| oci-mcp-security | OCI Security MCP Server | 8 | IAM, Cloud Guard | stdio |
| oci-mcp-logan | OCI Logging Analytics | 20 | Log search, MITRE analysis | HTTP |
| oci-mcp-observability | OCI Observability Server | 29 | Monitoring, alarms | stdio |

**Total: 164 unique tools** (after deduplication from unified server)

## API Endpoints

### Health Check
```http
GET /health
```
Returns agent health status including MCP server connections and OTEL status.

### MCP Servers
```http
GET /api/mcp/servers
```
Lists all configured MCP servers and their connection status.

### MCP Tools
```http
GET /api/mcp/tools
```
Returns the complete tool catalog from all connected servers.

### Tool Execution
```http
POST /api/mcp/tools/{toolName}
Content-Type: application/json

{
  "compartment": "Adrian_Birzu",
  "other_param": "value"
}
```
Executes a specific MCP tool with the provided arguments.

### Slack Diagnostics
```http
GET /api/slack/diagnostics
```
Returns Slack bot connection status and recent activity.

### Observability Status
```http
GET /api/observability/status
```
Returns OpenTelemetry tracing configuration status.

### Test OTEL
```http
POST /api/observability/otel/test
```
Sends a test span to OCI APM to verify connectivity.

## Configuration

### Environment Variables

```bash
# Server Configuration
PORT=3002                           # HTTP server port

# LLM Provider Configuration
LLM_PROVIDER=anthropic              # anthropic, openai
LLM_MODEL=claude-sonnet-4-20250514  # Model to use
ANTHROPIC_API_KEY=[Link to Secure Variable: ANTHROPIC_API_KEY]        # Anthropic API key
OPENAI_API_KEY=[Link to Secure Variable: OPENAI_API_KEY]              # OpenAI API key (alternative)

# Slack Bot Configuration
SLACK_BOT_TOKEN=[Link to Secure Variable: SLACK_BOT_TOKEN]            # Slack bot token
SLACK_APP_TOKEN=[Link to Secure Variable: SLACK_APP_TOKEN]            # Slack app token (Socket Mode)
SLACK_SIGNING_SECRET=...            # Slack signing secret
SLACK_BOT_ENABLED=true              # Enable/disable Slack bot

# MCP Server Configuration
MCP_OCI_PYTHON=/path/to/python      # Python interpreter for MCP servers
MCP_OCI_PATH=/path/to/mcp-oci       # Path to MCP servers repository

# OpenTelemetry / OCI APM
OCI_APM_ENDPOINT=[Link to Secure Variable: OCI_APM_ENDPOINT]
OCI_APM_PRIVATE_DATA_KEY=[Link to Secure Variable: OCI_APM_PRIVATE_DATA_KEY]
OTEL_SERVICE_NAME=oci-ops-agent     # Service name in traces
OTEL_TRACING_ENABLED=true           # Enable/disable tracing
```

### MCP Server Configuration (data/mcp-servers-ops.json)

```json
{
  "version": 1,
  "description": "Operations-focused MCP servers",
  "servers": [
    {
      "id": "oci-mcp-unified",
      "name": "OCI Unified MCP Server",
      "command": "${MCP_OCI_PYTHON}",
      "args": ["-m", "mcp_servers.unified.server"],
      "cwd": "${MCP_OCI_PATH}",
      "enabled": true,
      "transport": "stdio",
      "autoConnect": true
    }
  ]
}
```

## Agent Capabilities

The Operations Agent can help with:

### Compute Operations
- List, start, stop, restart instances
- Get instance metrics (CPU, memory, network)
- Instance pool management

### Networking
- VCN and subnet management
- Security list configuration
- Load balancer operations

### Cost Management
- Spending analysis and forecasting
- Budget alerts and tracking
- Resource optimization recommendations

### Security
- IAM user and policy management
- Cloud Guard problem detection
- Security zone compliance

### Observability
- Log analytics queries
- Alarm management
- Metrics analysis

## Slack Bot Usage

### Basic Commands
```
ping                    # Check if bot is online
diagnostics             # Get bot status
status                  # Get bot status
```

### Quick Actions Menu
```
menu                    # Show quick actions menu
```

### Natural Language Queries
```
@bot list my running instances
@bot what's my current cloud spend?
@bot show security problems in my tenancy
```

### Compute Instance Wizard
```
@bot create a compute instance
@bot I need a new VM
```
This triggers an interactive wizard for instance creation.

## Starting the Agent

### Development
```bash
cd /Users/abirzu/dev/MCP/oci-operations-agent
npm install
npm run server
```

### Production
```bash
npm start
```

### Type Checking
```bash
npm run typecheck
```

### Running Tests
```bash
npm test
```

## Observability

### OTEL Tracing Spans

The agent creates traces for:
- **LLM Calls**: `{operation} {model}` (e.g., "chat claude-sonnet-4-20250514")
- **Agent Invocations**: `agent.{type}.invoke`
- **Tool Executions**: `mcp.tool.{toolName}`
- **Slack Messages**: `slack.message.handle`
- **Workflows**: `workflow.{type}`

### Viewing Traces in OCI APM
1. Navigate to OCI Console > Observability > APM
2. Open your APM Domain
3. Go to Trace Explorer
4. Filter by service name "oci-ops-agent" (or your configured name)

## Project Structure

```
oci-operations-agent/
├── server.ts                    # Main server entry point
├── package.json                 # Dependencies and scripts
├── tsconfig.json               # TypeScript configuration
├── data/
│   └── mcp-servers-ops.json    # MCP server configurations
├── services/
│   ├── langchainAgent.ts       # LangChain ReAct agent
│   ├── mcpClient/              # MCP server connection
│   │   ├── index.ts
│   │   ├── ServerRegistry.ts
│   │   ├── ToolCatalog.ts
│   │   └── ConfigStore.ts
│   ├── slack/                  # Slack bot integration
│   │   ├── SlackBot.ts
│   │   ├── intent/
│   │   ├── ui/
│   │   ├── handlers/
│   │   └── config/
│   ├── observability/          # OpenTelemetry tracing
│   │   ├── OtelTracing.ts
│   │   ├── AgentObservability.ts
│   │   └── index.ts
│   ├── providers/              # LLM provider clients
│   │   ├── ProviderRegistry.ts
│   │   ├── AnthropicNativeClient.ts
│   │   └── CircuitBreaker.ts
│   ├── wizards/                # Interactive wizards
│   │   └── ComputeInstanceWizard.ts
│   └── logging/                # Structured logging
│       ├── StructuredLogger.ts
│       └── ErrorAggregator.ts
├── routes/
│   └── computeRoutes.ts        # Compute-specific routes
└── middleware/
    └── logging.ts              # HTTP logging middleware
```

## Dependencies

### Core
- **express**: HTTP server framework
- **@langchain/core**: LangChain core library
- **@langchain/anthropic**: Anthropic Claude integration
- **@langchain/langgraph**: LangGraph for ReAct agent
- **@modelcontextprotocol/sdk**: MCP client SDK
- **@slack/bolt**: Slack bot framework

### Observability
- **@opentelemetry/sdk-node**: OpenTelemetry SDK
- **@opentelemetry/exporter-trace-otlp-http**: OTLP exporter
- **@opentelemetry/instrumentation-express**: Express instrumentation
- **@opentelemetry/instrumentation-http**: HTTP instrumentation
- **pino**: Structured logging

## Troubleshooting

### MCP Servers Not Connecting
1. Verify `MCP_OCI_PYTHON` points to a valid Python interpreter
2. Check `MCP_OCI_PATH` is set correctly
3. Ensure MCP server Python dependencies are installed
4. Check server logs for connection errors

### Slack Bot Not Responding
1. Verify Slack tokens are set correctly
2. Check Socket Mode is enabled in Slack app settings
3. Review bot scopes (chat:write, app_mentions:read, etc.)
4. Check `/api/slack/diagnostics` for error details

### OTEL Traces Not Appearing
1. Verify `OCI_APM_ENDPOINT` is correct
2. Check `OCI_APM_PRIVATE_DATA_KEY` is valid
3. Traces may take 1-2 minutes to appear in APM
4. Use `/api/observability/otel/test` to verify connectivity

## Related Documentation

- [MCP Servers Reference](./MCP_SERVERS_REFERENCE.md) - Detailed documentation for all MCP servers
- [MCP HTTP Gateway](../shared_test_infra/README.md) - HTTP gateway for MCP servers
