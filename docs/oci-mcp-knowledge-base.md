# Knowledge Base: Running MCP Servers on OCI

This knowledge base covers how to run any MCP server on Oracle Cloud Infrastructure, integrate it with the MCP Gateway, and expose it to AI clients.

## Table of Contents

- [Overview: MCP on OCI](#overview-mcp-on-oci)
- [OCI Hosting Options Comparison](#oci-hosting-options-comparison)
- [Running MCP Servers on OKE](#running-mcp-servers-on-oke)
- [Running MCP Servers on OCI Data Science](#running-mcp-servers-on-oci-data-science)
- [Running MCP Servers on OCI Container Instances](#running-mcp-servers-on-oci-container-instances)
- [Oracle Integration Cloud MCP Server](#oracle-integration-cloud-mcp-server)
- [Oracle Database MCP Server (Autonomous DB)](#oracle-database-mcp-server-autonomous-db)
- [Connecting External LLMs to OCI MCP Servers](#connecting-external-llms-to-oci-mcp-servers)
- [Registering Any MCP Server with the Gateway](#registering-any-mcp-server-with-the-gateway)
- [Security Architecture](#security-architecture)
- [Troubleshooting](#troubleshooting)

---

## Overview: MCP on OCI

The Model Context Protocol (MCP) enables AI agents to interact with external tools and data sources. OCI provides multiple hosting options for MCP servers, each suited to different use cases:

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Server Ecosystem on OCI                  │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ OKE      │  │ Data     │  │Container │  │ OCI Functions    │ │
│  │(K8s pods)│  │ Science  │  │Instances │  │ (serverless)     │ │
│  │          │  │ (Model   │  │(managed  │  │                  │ │
│  │ Best for │  │  Deploy) │  │ docker)  │  │ Best for         │ │
│  │ prod,    │  │          │  │          │  │ lightweight,     │ │
│  │ multi-   │  │ Best for │  │ Best for │  │ event-driven     │ │
│  │ server   │  │ ML teams,│  │ simple   │  │ tool calls       │ │
│  │ gateway  │  │ notebook │  │ single   │  │                  │ │
│  │          │  │ workflows│  │ server   │  │                  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
│         │            │            │               │              │
│         └────────────┴────────────┴───────────────┘              │
│                           │                                      │
│                    ┌──────┴───────┐                               │
│                    │ MCP Gateway  │                               │
│                    │ (aggregator) │                               │
│                    └──────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### MCP Transport on OCI

| Transport | OCI Use | Notes |
|-----------|---------|-------|
| **stdio** | OKE (sidecar/subprocess) | Gateway spawns the server as a child process |
| **Streamable HTTP** | All platforms | Primary transport for networked deployment |
| **SSE** | Legacy only | Deprecated in MCP spec, use Streamable HTTP |

---

## OCI Hosting Options Comparison

| Feature | OKE | Data Science | Container Instances | Functions |
|---------|-----|-------------|-------------------|-----------|
| **Best for** | Production, multi-server | ML teams, notebooks | Simple, single server | Event-driven |
| **Scaling** | HPA, manual | Instance count | Manual | Auto |
| **Auth** | Resource/Instance principal | Resource principal | Resource principal | Resource principal |
| **Networking** | VCN + LB + Ingress | Private endpoint | VCN + private IP | VCN + API GW |
| **Cost** | Worker nodes | Model deploy shape | Container shape | Per-invocation |
| **Startup time** | Seconds (pod) | Minutes (deploy) | Minutes (CI) | Cold start ~2s |
| **Persistence** | Volumes | Block storage | Volumes | None |
| **Gateway support** | Native | Via HTTP backend | Via HTTP backend | Via HTTP/adapter |
| **Complexity** | High | Medium | Low | Low |

---

## Running MCP Servers on OKE

### Any MCP Server as a K8s Deployment

To run any MCP server (Python, Node.js, Go, etc.) on OKE:

#### 1. Containerize the MCP Server

```dockerfile
# Example: Generic Python MCP Server
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Must use Streamable HTTP transport for network access
ENV MCP_TRANSPORT=streamable_http
ENV MCP_PORT=8000
EXPOSE 8000

CMD ["python", "-m", "my_mcp_server"]
```

#### 2. Create the K8s Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-mcp-server
  namespace: mcp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-mcp-server
  template:
    metadata:
      labels:
        app: my-mcp-server
    spec:
      containers:
        - name: server
          image: <region>.ocir.io/<namespace>/my-mcp-server:latest
          ports:
            - containerPort: 8000
          env:
            - name: OCI_CLI_AUTH
              value: "resource_principal"
---
apiVersion: v1
kind: Service
metadata:
  name: my-mcp-server
  namespace: mcp
spec:
  type: ClusterIP
  ports:
    - port: 8000
      targetPort: 8000
  selector:
    app: my-mcp-server
```

#### 3. Register with the Gateway

Add to `gateway.json` or a drop-in file in `backends.d/`:

```json
{
  "name": "my-mcp-server",
  "description": "My custom MCP server",
  "transport": "streamable_http",
  "url": "http://my-mcp-server.mcp.svc.cluster.local:8000/mcp",
  "auth_method": "none",
  "namespace_tools": true,
  "tags": ["custom", "in-cluster"]
}
```

### Node.js MCP Servers on OKE

```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
ENV MCP_TRANSPORT=streamable-http
EXPOSE 3000
CMD ["node", "server.js"]
```

---

## Running MCP Servers on OCI Data Science

OCI Data Science Model Deployments provide managed HTTP endpoints with resource principal authentication.

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│ OCI Data Science                                          │
│                                                           │
│  ┌─────────────────┐     ┌──────────────────────────┐    │
│  │ Notebook Session │     │ Model Deployment          │    │
│  │                  │     │                           │    │
│  │ - Develop MCP    │────▶│ - Runs MCP server (HTTP)  │    │
│  │   server code    │     │ - Resource principal auth  │    │
│  │ - Test locally   │     │ - Auto-scaling instances   │    │
│  │                  │     │ - Health monitoring        │    │
│  └─────────────────┘     │                           │    │
│                           │ Endpoint:                 │    │
│                           │ https://modeldeployment.  │    │
│                           │ <region>.oci.customer-oci │    │
│                           │ .com/<ocid>/predict       │    │
│                           └──────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### Step-by-Step

1. **Create a Data Science project and notebook session**
2. **Develop your MCP server** in the notebook
3. **Create a model artifact** with `score.py` entry point
4. **Deploy** as a Model Deployment
5. **Register** the deployment URL as a gateway backend

### score.py Pattern

```python
"""MCP Server running as an OCI Data Science Model Deployment.

The score.py file is the standard entry point for OCI Data Science.
- load_model() is called once at startup
- predict() handles incoming requests
"""
import os
import json
import threading
from http.server import HTTPServer

# Set OCI auth to resource principal (automatic in Data Science)
os.environ["OCI_CLI_AUTH"] = "resource_principal"

_mcp_server = None

def load_model():
    """Initialize the MCP server at deployment startup."""
    global _mcp_server
    # Import and start your MCP server
    from my_mcp_server import create_server
    _mcp_server = create_server()

    # Start Streamable HTTP in background
    thread = threading.Thread(
        target=_mcp_server.run,
        kwargs={"transport": "streamable-http", "host": "0.0.0.0", "port": 8080},
        daemon=True
    )
    thread.start()
    return _mcp_server

def predict(data, model=None):
    """Handle incoming requests (health check / proxy)."""
    return {"status": "healthy", "server": "mcp"}
```

### Key Considerations

- Data Science deployments use **resource principals** automatically
- The deployment runs in a **private subnet** by default
- Access it via the gateway or OCI API Gateway
- Supports **custom Docker images** via BYOC (Bring Your Own Container)
- Model deployment logs available in OCI Logging

---

## Running MCP Servers on OCI Container Instances

Simplest option for running a single containerized MCP server.

### Deploy

```bash
# Build and push your image to OCIR
docker build -t <region>.ocir.io/<namespace>/my-mcp:latest .
docker push <region>.ocir.io/<namespace>/my-mcp:latest

# Create container instance
oci container-instances container-instance create \
  --compartment-id <COMPARTMENT_OCID> \
  --availability-domain <AD> \
  --shape "CI.Standard.E4.Flex" \
  --shape-config '{"ocpus": 1, "memoryInGBs": 2}' \
  --display-name "my-mcp-server" \
  --containers '[{
    "imageUrl": "<region>.ocir.io/<namespace>/my-mcp:latest",
    "displayName": "mcp-server",
    "environmentVariables": {
      "OCI_CLI_AUTH": "resource_principal",
      "MCP_TRANSPORT": "streamable_http",
      "MCP_PORT": "8000"
    }
  }]' \
  --vnics '[{
    "subnetId": "<PRIVATE_SUBNET_OCID>",
    "isPublicIpAssigned": false
  }]'
```

### Access

The container instance gets a private IP. Register it with the gateway:

```json
{
  "name": "ci-mcp-server",
  "transport": "streamable_http",
  "url": "http://<PRIVATE_IP>:8000/mcp",
  "auth_method": "none",
  "tags": ["oci", "container-instance"]
}
```

---

## Oracle Integration Cloud MCP Server

Oracle Integration Cloud (OIC) 3 provides a built-in MCP server that exposes integration flows as MCP tools.

### Setup

1. **Enable MCP in OIC**: Navigate to your OIC instance → Settings → Enable MCP Server
2. **Create integrations**: Build integration flows that expose business logic
3. **MCP endpoint**: OIC exposes an MCP-compatible endpoint automatically

### Connecting OIC to the Gateway

```json
{
  "name": "oracle-integration",
  "description": "Oracle Integration Cloud MCP Server",
  "transport": "streamable_http",
  "url": "https://<oic-instance>.integration.ocp.oraclecloud.com/mcp",
  "auth_method": "bearer_token",
  "bearer_token": "<oic-access-token>",
  "namespace_tools": true,
  "tags": ["oci", "oic", "integration"]
}
```

### OIC + AI Agents

OIC 3 supports AI Agent projects that can use MCP servers:

1. Create an AI Agent project in OIC
2. Enable MCP in the project settings
3. The agent can call MCP tools from integration flows
4. External MCP servers can be registered as connections

Reference: [Oracle Integration MCP Server docs](https://docs.oracle.com/en/cloud/paas/application-integration/int-get-started/oracle-integration-mcp-server.html)

---

## Oracle Database MCP Server (Autonomous DB)

Oracle provides an official MCP server for database operations. See [github.com/oracle/mcp](https://github.com/oracle/mcp).

### Oracle Database MCP Server

The Oracle MCP server provides tools for:
- Executing SQL queries
- Managing database objects (tables, views, procedures)
- Performance monitoring and tuning
- Data export/import

### Running with Autonomous DB

```bash
# Install the Oracle MCP server
pip install oracle-mcp-server

# Configure connection to Autonomous DB
export ORACLE_DSN="(description=(address=(protocol=tcps)(port=1522)(host=adb.<region>.oraclecloud.com))(connect_data=(service_name=<service>_high)))"
export ORACLE_USER="ADMIN"
export ORACLE_PASSWORD_SECRET="ocid1.vaultsecret.oc1..."
export ORACLE_WALLET_LOCATION="/opt/oracle/wallet"

# Run with Streamable HTTP for network access
python -m oracle_mcp_server --transport streamable-http --port 8000
```

### Register with the Gateway

```json
{
  "name": "oracle-db",
  "description": "Oracle Autonomous Database MCP Server",
  "transport": "streamable_http",
  "url": "http://oracle-db-mcp.mcp.svc.cluster.local:8000/mcp",
  "auth_method": "resource_principal",
  "namespace_tools": true,
  "tags": ["oci", "database", "adb"]
}
```

### As a Kubernetes Sidecar

Run the Oracle DB MCP server alongside your application:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oracle-db-mcp
  namespace: mcp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oracle-db-mcp
  template:
    spec:
      containers:
        - name: mcp-server
          image: <region>.ocir.io/<namespace>/oracle-db-mcp:latest
          ports:
            - containerPort: 8000
          env:
            - name: ORACLE_DSN
              valueFrom:
                secretKeyRef:
                  name: oracle-db-secrets
                  key: dsn
            - name: ORACLE_USER
              valueFrom:
                secretKeyRef:
                  name: oracle-db-secrets
                  key: username
            - name: OCI_CLI_AUTH
              value: "resource_principal"
          volumeMounts:
            - name: wallet
              mountPath: /opt/oracle/wallet
              readOnly: true
      volumes:
        - name: wallet
          secret:
            secretName: oracle-db-wallet
```

---

## Connecting External LLMs to OCI MCP Servers

### Claude Desktop

**Direct connection** via Streamable HTTP:

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
// %APPDATA%\Claude\claude_desktop_config.json (Windows)
{
  "mcpServers": {
    "oci-cloud": {
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer <jwt-token>"
      }
    }
  }
}
```

### Cline (VS Code)

Add to `.vscode/mcp.json` or Cline MCP settings:

```json
{
  "mcpServers": {
    "oci-cloud": {
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer <jwt-token>"
      }
    }
  }
}
```

### ChatGPT (via Actions)

ChatGPT uses OpenAPI-based Actions. You need a REST adapter:

1. Deploy the REST-to-MCP adapter alongside the gateway (see deployment guide)
2. Create an OpenAPI schema describing the available tools
3. In ChatGPT GPT Builder, import the schema
4. Configure OAuth 2.0 authentication
5. The GPT can now call OCI tools

**Key difference**: ChatGPT does not speak MCP protocol natively. It uses REST + OpenAPI. The adapter translates REST calls to MCP JSON-RPC.

### Google Gemini

Gemini uses function calling with HTTP endpoints:

1. Define MCP tools as Gemini FunctionDeclarations
2. When Gemini makes a function call, proxy it to the MCP Gateway
3. Return the result to Gemini

See the deployment guide for code examples.

### OpenAI API (direct)

```python
import openai
import httpx

client = openai.OpenAI()

# Define MCP tools as OpenAI function specs
tools = [{
    "type": "function",
    "function": {
        "name": "oci_compute_list_instances",
        "description": "List OCI compute instances",
        "parameters": {
            "type": "object",
            "properties": {
                "compartment_id": {"type": "string"},
                "region": {"type": "string"}
            }
        }
    }
}]

# When the model calls a function, proxy to MCP Gateway
def execute_tool(name, args):
    resp = httpx.post("https://mcp.example.com/mcp", json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": name, "arguments": args},
        "id": 1
    }, headers={"Authorization": "Bearer <token>"})
    return resp.json()["result"]
```

---

## Registering Any MCP Server with the Gateway

### Method 1: Gateway Config File

Add the backend directly to `gateway.json`:

```json
{
  "backends": [
    {
      "name": "my-server",
      "transport": "streamable_http",
      "url": "http://my-server:8000/mcp",
      "namespace_tools": true
    }
  ]
}
```

### Method 2: Drop-in Config Directory

Create a JSON file in `backends.d/`:

```bash
# backends.d/my-server.json
{
  "name": "my-server",
  "transport": "streamable_http",
  "url": "http://my-server:8000/mcp"
}
```

Run the gateway with: `oci-mcp-gateway --backends-dir ./backends.d`

### Method 3: Auto-Discovery

Place a `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["-m", "my_server"],
      "env": {}
    }
  }
}
```

Run: `oci-mcp-gateway --scan /path/to/projects`

### Method 4: Kubernetes ConfigMap

Add backend configs via K8s ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: extra-backends
  namespace: mcp
data:
  oracle-db.json: |
    {
      "name": "oracle-db",
      "transport": "streamable_http",
      "url": "http://oracle-db-mcp.mcp.svc.cluster.local:8000/mcp"
    }
```

Mount it and use `--backends-dir`:

```yaml
volumeMounts:
  - name: extra-backends
    mountPath: /etc/mcp/backends.d
volumes:
  - name: extra-backends
    configMap:
      name: extra-backends
```

---

## Security Architecture

### End-to-End Authentication Flow

```
External Client                     OCI
─────────────────                   ───

1. Client obtains JWT from IdP
   (OCI IAM, Auth0, Okta, etc.)

2. Client sends request ──────────▶ OCI API Gateway
   with Bearer token                ├── Validates JWT signature
                                    ├── Checks issuer, audience, expiry
                                    ├── Rate limiting
                                    └── Forwards to internal LB

3. Internal LB ──────────────────▶ MCP Gateway
                                    ├── Validates Bearer token
                                    ├── Checks tool-level scopes
                                    ├── Audit logs the request
                                    └── Routes to backend

4. MCP Gateway ──────────────────▶ MCP Server (backend)
                                    ├── Resource principal auth to OCI
                                    ├── Executes tool
                                    └── Returns result

5. Result flows back ◀────────── Client
```

### IAM Policies for Different Services

```bash
# OKE pods
Allow dynamic-group oke-mcp-pods to read all-resources in compartment <name>

# Data Science deployments
Allow dynamic-group datascience-mcp to read all-resources in compartment <name>

# Container Instances
Allow dynamic-group ci-mcp to read all-resources in compartment <name>

# OCI Functions
Allow dynamic-group fn-mcp to read all-resources in compartment <name>
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Invalid or expired JWT | Refresh token, check issuer/audience config |
| `Connection refused` | Server not listening | Check transport is `streamable_http`, verify port |
| `Resource principal not configured` | Missing dynamic group | Create dynamic group + IAM policy |
| `Timeout` connecting to backend | Network/firewall | Check security lists, NSGs, and VCN routing |
| `No tools found` | Backend not connected | Check `gateway_list_backends` tool, verify URL |
| `CORS error` from browser | Missing CORS headers | Configure `cors_origins` in gateway auth config |

### Debugging Commands

```bash
# Check gateway health
curl -s http://gateway:9000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"gateway_health","arguments":{}},"id":1}'

# List backends
curl -s http://gateway:9000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"gateway_list_backends","arguments":{}},"id":1}'

# Test backend connectivity from gateway pod
kubectl exec -n mcp deploy/oci-mcp-gateway -- \
  curl -s http://oci-mcp-server.mcp.svc.cluster.local:8000/mcp

# Check resource principal availability
kubectl exec -n mcp deploy/oci-mcp-server -- \
  python -c "import oci; print(oci.auth.signers.get_resource_principals_signer())"
```
