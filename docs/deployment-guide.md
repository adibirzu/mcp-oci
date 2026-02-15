# OCI MCP Server - Deployment Guide

This guide covers deploying the OCI MCP Server and Gateway on Oracle Cloud Infrastructure (OCI), with access from both internal OCI services and external AI clients (Claude Desktop, ChatGPT, Gemini, Cline).

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Deployment Option 1: OKE (Kubernetes)](#deployment-option-1-oke-kubernetes)
- [Deployment Option 2: OCI Data Science](#deployment-option-2-oci-data-science)
- [Deployment Option 3: OCI Container Instances](#deployment-option-3-oci-container-instances)
- [Deployment Option 4: OCI Functions (Serverless)](#deployment-option-4-oci-functions-serverless)
- [External Access for AI Clients](#external-access-for-ai-clients)
- [OCI API Gateway Integration](#oci-api-gateway-integration)
- [Security Best Practices](#security-best-practices)
- [Monitoring and Observability](#monitoring-and-observability)

---

## Architecture Overview

```
                         ┌─────────────────────────────────────────┐
                         │           OCI Tenancy                   │
                         │                                         │
    External Clients     │   ┌──────────────┐   ┌──────────────┐  │
    ─────────────────    │   │  OCI API GW   │   │ OCI LB (pub) │  │
    Claude Desktop ──────┼──▶│  (OAuth/TLS)  │──▶│              │  │
    ChatGPT Actions ─────┼──▶│              │   │              │  │
    Gemini ──────────────┼──▶│              │   │              │  │
    Cline ───────────────┼──▶│              │   │              │  │
                         │   └──────────────┘   └──────┬───────┘  │
                         │                             │          │
                         │   ┌─────────────────────────┼────────┐ │
                         │   │        OKE Cluster       │        │ │
                         │   │                          ▼        │ │
    Internal Clients     │   │   ┌──────────────────────────┐    │ │
    ─────────────────    │   │   │   MCP Gateway (:9000)    │    │ │
    OCI AI Agents ───────┼───┼──▶│   (Streamable HTTP)      │    │ │
    OCI Data Science ────┼───┼──▶│   (JWT / Bearer Auth)    │    │ │
    OCI Functions ───────┼───┼──▶│                          │    │ │
    Private VCN Apps ────┼───┼──▶└────┬───────────┬─────────┘    │ │
                         │   │        │           │              │ │
                         │   │   ┌────▼────┐ ┌────▼────┐         │ │
                         │   │   │OCI MCP  │ │External │         │ │
                         │   │   │Server   │ │MCP Svrs │         │ │
                         │   │   │(:8000)  │ │(HTTP)   │         │ │
                         │   │   └─────────┘ └─────────┘         │ │
                         │   └───────────────────────────────────┘ │
                         │                                         │
                         │   ┌─────────────────┐                   │
                         │   │  OCI Services    │                  │
                         │   │  Compute, DB,    │                  │
                         │   │  Network, etc.   │                  │
                         │   └─────────────────┘                   │
                         └─────────────────────────────────────────┘
```

### Access Patterns

| Client Type | Access Path | Authentication |
|------------|-------------|----------------|
| Claude Desktop / Cline | Internet → OCI API GW/LB → Gateway | Bearer token (JWT) |
| ChatGPT Actions | Internet → OCI API GW → Gateway | OAuth 2.0 |
| Google Gemini | Internet → OCI API GW/LB → Gateway | Bearer token |
| OCI AI Agents | Private VCN → Gateway (internal LB) | Resource principal / Bearer |
| OCI Data Science | Private VCN → Gateway (internal LB) | Resource principal |
| OCI Functions | Private VCN → Gateway (internal LB) | Resource principal |
| Other OKE pods | ClusterIP → Gateway | Service mesh / Bearer |

---

## Deployment Option 1: OKE (Kubernetes)

**Recommended for production.** Run both the MCP Server and Gateway as Kubernetes deployments on OKE.

### Prerequisites

- OKE cluster (v1.28+) with at least 2 worker nodes
- OCI Container Registry (OCIR) for images
- `kubectl` and `oci` CLI configured
- OCI Dynamic Group + IAM policies for pod workload identity

### Step 1: Create IAM Policies

```bash
# Create a dynamic group for MCP server pods
# Match by compartment + Kubernetes namespace
oci iam dynamic-group create \
  --name mcp-server-pods \
  --description "MCP Server pods running on OKE" \
  --matching-rule "ALL {resource.type='cluster', resource.compartment.id='<COMPARTMENT_OCID>'}"

# Grant the dynamic group access to OCI services
oci iam policy create \
  --compartment-id <COMPARTMENT_OCID> \
  --name mcp-server-policy \
  --description "Allow MCP server to read OCI resources" \
  --statements '[
    "Allow dynamic-group mcp-server-pods to read all-resources in compartment <COMPARTMENT_NAME>",
    "Allow dynamic-group mcp-server-pods to use metrics in compartment <COMPARTMENT_NAME>",
    "Allow dynamic-group mcp-server-pods to read log-content in compartment <COMPARTMENT_NAME>"
  ]'
```

### Step 2: Build and Push Container Images

```bash
# Set your OCIR coordinates
export OCIR_REGION=us-ashburn-1     # Your OCI region
export OCIR_NAMESPACE=mytenancy     # Your tenancy namespace
export OCIR_REPO=oci-mcp            # Repository name

# Login to OCIR
docker login ${OCIR_REGION}.ocir.io -u "${OCIR_NAMESPACE}/oracleidentitycloudservice/<email>"

# Build the MCP Server image
docker build --target server \
  -t ${OCIR_REGION}.ocir.io/${OCIR_NAMESPACE}/${OCIR_REPO}/oci-mcp-server:latest .

# Build the MCP Gateway image
docker build --target gateway \
  -t ${OCIR_REGION}.ocir.io/${OCIR_NAMESPACE}/${OCIR_REPO}/oci-mcp-gateway:latest .

# Push both images
docker push ${OCIR_REGION}.ocir.io/${OCIR_NAMESPACE}/${OCIR_REPO}/oci-mcp-server:latest
docker push ${OCIR_REGION}.ocir.io/${OCIR_NAMESPACE}/${OCIR_REPO}/oci-mcp-gateway:latest
```

### Step 3: Create Kubernetes Secrets

```bash
# OCIR pull secret
kubectl create namespace mcp

kubectl create secret docker-registry ocir-secret -n mcp \
  --docker-server=${OCIR_REGION}.ocir.io \
  --docker-username="${OCIR_NAMESPACE}/oracleidentitycloudservice/<email>" \
  --docker-password='<auth-token>'

# JWT public key for gateway auth (generate or use existing)
openssl genrsa -out jwt-private.pem 2048
openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem

kubectl create secret generic gateway-jwt-keys -n mcp \
  --from-file=public.pem=jwt-public.pem
```

### Step 4: Configure and Deploy

```bash
# Edit the configuration files
# 1. deploy/k8s/oci-config.yaml - Set your region and compartment
# 2. deploy/k8s/gateway-configmap.yaml - Configure backends
# 3. deploy/k8s/server-deployment.yaml - Set OCIR image path
# 4. deploy/k8s/gateway-deployment.yaml - Set OCIR image path

# Apply all manifests
kubectl apply -k deploy/k8s/

# Verify deployment
kubectl get pods -n mcp
kubectl get svc -n mcp

# Check gateway logs
kubectl logs -n mcp -l app.kubernetes.io/name=oci-mcp-gateway -f

# Get the external LB IP for client access
kubectl get svc oci-mcp-gateway -n mcp -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### Step 5: Verify

```bash
# Test the gateway endpoint
GATEWAY_IP=$(kubectl get svc oci-mcp-gateway -n mcp -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Health check (no auth for health endpoint)
curl -s http://${GATEWAY_IP}:9000/mcp | head -20

# Test with a Bearer token
curl -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
  http://${GATEWAY_IP}:9000/mcp
```

### Horizontal Scaling

The gateway runs in `--stateless` mode by default on OKE, enabling horizontal scaling:

```bash
# Scale gateway replicas
kubectl scale deployment oci-mcp-gateway -n mcp --replicas=4

# Scale server replicas
kubectl scale deployment oci-mcp-server -n mcp --replicas=3

# Or use HPA
kubectl autoscale deployment oci-mcp-gateway -n mcp \
  --min=2 --max=10 --cpu-percent=70
```

---

## Deployment Option 2: OCI Data Science

Host MCP servers as OCI Data Science Model Deployments. This is ideal for teams already using OCI Data Science for ML workflows.

### How It Works

OCI Data Science Model Deployments provide a managed HTTP endpoint. The MCP server runs as a custom model with Streamable HTTP transport.

### Step 1: Create the Deployment Artifact

```python
# score.py - OCI Data Science model score file
"""OCI MCP Server as a Data Science Model Deployment."""
import os
import threading

def load_model():
    """Called once when the model deployment starts."""
    # Set transport to streamable HTTP
    os.environ["OCI_MCP_TRANSPORT"] = "streamable_http"
    os.environ["OCI_MCP_PORT"] = "8080"
    os.environ["OCI_CLI_AUTH"] = "resource_principal"

    # Start MCP server in background thread
    from mcp_server_oci.server import main
    thread = threading.Thread(target=main, daemon=True)
    thread.start()

    return {"status": "MCP server started"}

def predict(data, model=None):
    """Health check endpoint for Data Science."""
    return {"status": "healthy", "type": "mcp-server"}
```

### Step 2: Create Model Artifact

```bash
# Package the project as a model artifact
mkdir -p model_artifact
cp -r src/ model_artifact/
cp score.py model_artifact/
cp pyproject.toml model_artifact/

# Create conda environment YAML
cat > model_artifact/environment.yaml << 'EOF'
name: mcp-server
channels:
  - defaults
  - conda-forge
dependencies:
  - python=3.12
  - pip
  - pip:
    - mcp>=1.0.0
    - fastmcp>=2.14.1
    - oci>=2.164.2
    - pydantic>=2.5.0
    - httpx>=0.25.0
    - structlog>=24.0.0
EOF

# Upload to OCI Data Science catalog
oci data-science model create \
  --compartment-id <COMPARTMENT_OCID> \
  --project-id <PROJECT_OCID> \
  --display-name "OCI MCP Server" \
  --model-artifact model_artifact/
```

### Step 3: Create Model Deployment

```bash
oci data-science model-deployment create \
  --compartment-id <COMPARTMENT_OCID> \
  --project-id <PROJECT_OCID> \
  --model-id <MODEL_OCID> \
  --display-name "OCI MCP Server Deployment" \
  --instance-shape-name "VM.Standard.E4.Flex" \
  --instance-count 1 \
  --bandwidth-mbps 10
```

The deployment endpoint will be:
```
https://modeldeployment.<region>.oci.customer-oci.com/<deployment-ocid>/predict
```

### Connecting via the Gateway

Add the Data Science deployment as a backend in `gateway.json`:

```json
{
  "name": "oci-datascience",
  "description": "OCI MCP Server hosted on Data Science",
  "transport": "streamable_http",
  "url": "https://modeldeployment.<region>.oci.customer-oci.com/<deployment-ocid>/mcp",
  "auth_method": "resource_principal",
  "tags": ["oci", "data-science"]
}
```

---

## Deployment Option 3: OCI Container Instances

Serverless containers without managing Kubernetes. Good for simple, single-server deployments.

### Deploy

```bash
# Create a container instance running the MCP server
oci container-instances container-instance create \
  --compartment-id <COMPARTMENT_OCID> \
  --availability-domain <AD> \
  --shape "CI.Standard.E4.Flex" \
  --shape-config '{"ocpus": 1, "memoryInGBs": 4}' \
  --display-name "oci-mcp-server" \
  --containers '[{
    "imageUrl": "<region>.ocir.io/<namespace>/oci-mcp/oci-mcp-server:latest",
    "displayName": "mcp-server",
    "environmentVariables": {
      "OCI_MCP_TRANSPORT": "streamable_http",
      "OCI_MCP_PORT": "8000",
      "OCI_CLI_AUTH": "resource_principal",
      "OCI_REGION": "<region>"
    }
  }]' \
  --vnics '[{
    "subnetId": "<SUBNET_OCID>",
    "isPublicIpAssigned": false
  }]'
```

The container instance gets a private IP within your VCN. Access it via the gateway or an internal load balancer.

---

## Deployment Option 4: OCI Functions (Serverless)

For lightweight, event-driven MCP access. Note: Functions have a 5-minute timeout, so this is best for simple tool calls.

### func.py

```python
import io
import json
from fdk import response

def handler(ctx, data: io.BytesIO = None):
    """OCI Function handler for MCP tool calls."""
    body = json.loads(data.getvalue())

    # Route to the appropriate MCP tool
    method = body.get("method", "")
    if method == "tools/list":
        # Return available tools
        result = list_tools()
    elif method == "tools/call":
        tool_name = body.get("params", {}).get("name", "")
        tool_args = body.get("params", {}).get("arguments", {})
        result = call_tool(tool_name, tool_args)
    else:
        result = {"error": f"Unknown method: {method}"}

    return response.Response(
        ctx,
        response_data=json.dumps({"jsonrpc": "2.0", "result": result, "id": body.get("id")}),
        headers={"Content-Type": "application/json"}
    )
```

---

## External Access for AI Clients

### Claude Desktop / Cline

Claude Desktop and Cline support remote MCP servers via Streamable HTTP:

```json
{
  "mcpServers": {
    "oci-cloud": {
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer <your-jwt-token>"
      }
    }
  }
}
```

For Claude Desktop, add this to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows).

For Cline, add this to `.vscode/mcp.json` or the Cline MCP settings.

### ChatGPT (Actions / GPTs)

ChatGPT connects to external services via **Actions** (formerly Plugins). Actions use an OpenAPI schema with OAuth authentication.

#### Step 1: Create an OpenAPI Wrapper

Since ChatGPT Actions expect REST+OpenAPI (not MCP protocol), you need a thin REST adapter. Deploy it alongside the gateway:

```python
# chatgpt_adapter.py - REST to MCP bridge
from fastapi import FastAPI, Header, HTTPException
import httpx

app = FastAPI(title="OCI MCP Tools for ChatGPT")
MCP_GATEWAY = "http://oci-mcp-gateway.mcp.svc.cluster.local:9000/mcp"

@app.get("/tools")
async def list_tools(authorization: str = Header()):
    """List available OCI tools."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(MCP_GATEWAY, json={
            "jsonrpc": "2.0", "method": "tools/list", "id": 1
        }, headers={"Authorization": authorization})
    return resp.json().get("result", {})

@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, body: dict, authorization: str = Header()):
    """Call an OCI tool by name."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(MCP_GATEWAY, json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": body},
            "id": 1
        }, headers={"Authorization": authorization})
    return resp.json().get("result", {})
```

#### Step 2: Create the OpenAPI Schema

```yaml
openapi: 3.1.0
info:
  title: OCI Cloud Tools
  version: 1.0.0
  description: Oracle Cloud Infrastructure management tools
servers:
  - url: https://mcp.example.com
paths:
  /tools:
    get:
      operationId: listTools
      summary: List available OCI tools
      responses:
        '200':
          description: Available tools
  /tools/{tool_name}:
    post:
      operationId: callTool
      summary: Execute an OCI tool
      parameters:
        - name: tool_name
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
      responses:
        '200':
          description: Tool result
```

#### Step 3: Configure in ChatGPT

1. Go to [ChatGPT GPT Builder](https://chat.openai.com/gpts/editor)
2. Create a new GPT or Action
3. Import the OpenAPI schema
4. Configure OAuth authentication pointing to your identity provider
5. Test the action

### Google Gemini

Gemini supports external tools via function calling with HTTP endpoints. Configure the gateway as a tool source:

```python
# Gemini function calling with MCP Gateway
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")

# Define MCP tools as Gemini function declarations
oci_tools = genai.protos.Tool(function_declarations=[
    genai.protos.FunctionDeclaration(
        name="oci_compute_list_instances",
        description="List compute instances in OCI",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "compartment_id": genai.protos.Schema(type=genai.protos.Type.STRING),
                "region": genai.protos.Schema(type=genai.protos.Type.STRING),
            }
        )
    )
])

model = genai.GenerativeModel("gemini-pro", tools=[oci_tools])

# When Gemini makes a function call, proxy it to the MCP Gateway
def handle_function_call(fc):
    import httpx
    resp = httpx.post("https://mcp.example.com/mcp", json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": fc.name, "arguments": dict(fc.args)},
        "id": 1
    }, headers={"Authorization": "Bearer <token>"})
    return resp.json()["result"]
```

---

## OCI API Gateway Integration

For production external access, use OCI API Gateway as a secure front-end:

### Benefits

- **TLS termination** with OCI Certificates
- **OAuth 2.0 / JWT validation** (built-in)
- **Rate limiting** and throttling
- **Request/response transformation**
- **WAF integration** for DDoS protection
- **Custom domains** with DNS management

### Setup

```bash
# 1. Create API Gateway
oci api-gateway gateway create \
  --compartment-id <COMPARTMENT_OCID> \
  --display-name "MCP API Gateway" \
  --endpoint-type PUBLIC \
  --subnet-id <PUBLIC_SUBNET_OCID>

# 2. Create API Deployment
# Point /mcp to the internal gateway LB
oci api-gateway deployment create \
  --compartment-id <COMPARTMENT_OCID> \
  --gateway-id <GATEWAY_OCID> \
  --display-name "MCP Endpoint" \
  --path-prefix "/v1" \
  --specification '{
    "routes": [{
      "path": "/mcp",
      "methods": ["POST", "GET"],
      "backend": {
        "type": "HTTP_BACKEND",
        "url": "http://<INTERNAL_LB_IP>:9000/mcp"
      },
      "requestPolicies": {
        "authentication": {
          "type": "JWT_AUTHENTICATION",
          "tokenHeader": "Authorization",
          "tokenAuthScheme": "Bearer",
          "issuers": ["https://auth.example.com"],
          "audiences": ["oci-mcp-gateway"],
          "publicKeys": {
            "type": "REMOTE_JWKS",
            "uri": "https://auth.example.com/.well-known/jwks.json"
          }
        },
        "rateLimiting": {
          "rateInRequestsPerSecond": 100,
          "rateKey": "CLIENT_IP"
        }
      }
    }]
  }'
```

### Architecture with API Gateway

```
Claude Desktop ──▶ OCI API GW (public, TLS, JWT) ──▶ Internal LB ──▶ MCP Gateway ──▶ MCP Servers
                   ├── Rate limiting
                   ├── WAF protection
                   ├── OAuth validation
                   └── Request logging
```

---

## Security Best Practices

### 1. Network Security

```
┌─────────────────────────────────────────────────┐
│ VCN: 10.0.0.0/16                                │
│                                                 │
│ ┌─────────────────┐  ┌───────────────────────┐  │
│ │ Public Subnet    │  │ Private Subnet         │  │
│ │ 10.0.1.0/24      │  │ 10.0.2.0/24           │  │
│ │                  │  │                        │  │
│ │ - API Gateway    │  │ - OKE Worker Nodes     │  │
│ │ - Public LB      │──│ - MCP Gateway Pods     │  │
│ │                  │  │ - MCP Server Pods      │  │
│ │                  │  │ - Internal LB          │  │
│ └─────────────────┘  └───────────────────────┘  │
│                                                 │
│ Security Lists:                                 │
│ - Public: 443 inbound from 0.0.0.0/0           │
│ - Private: 9000 from public subnet only        │
│ - Private: 8000 from MCP namespace pods only   │
└─────────────────────────────────────────────────┘
```

### 2. Authentication Layers

| Layer | Method | Purpose |
|-------|--------|---------|
| API Gateway | JWT / OAuth 2.0 | External client auth |
| MCP Gateway | Bearer token | Tool-level access control |
| MCP Server → OCI | Resource principal | OCI API authentication |

### 3. Principle of Least Privilege

```bash
# Read-only policy for MCP servers (default)
Allow dynamic-group mcp-server-pods to read all-resources in compartment <name>

# If mutations are needed (ALLOW_MUTATIONS=true)
Allow dynamic-group mcp-server-pods to manage instance-family in compartment <name>
Allow dynamic-group mcp-server-pods to manage database-family in compartment <name>
```

### 4. Secret Management

- Use OCI Vault for JWT keys and tokens
- Use Kubernetes Secrets with RBAC
- Never commit credentials to config files
- Rotate tokens regularly

---

## Monitoring and Observability

### OCI APM Integration

```bash
# Set APM environment variables in deployment
env:
  - name: OCI_APM_ENDPOINT
    valueFrom:
      secretKeyRef:
        name: oci-mcp-secrets
        key: apm-endpoint
  - name: OCI_APM_PRIVATE_DATA_KEY
    valueFrom:
      secretKeyRef:
        name: oci-mcp-secrets
        key: apm-data-key
```

### OCI Logging

Enable structured logging to OCI Logging service:

```bash
env:
  - name: OCI_LOGGING_ENABLED
    value: "true"
  - name: OCI_LOGGING_LOG_ID
    value: "ocid1.log.oc1..."
```

### Kubernetes Monitoring

```bash
# View gateway metrics
kubectl top pods -n mcp

# View logs
kubectl logs -n mcp -l app.kubernetes.io/name=oci-mcp-gateway --tail=100 -f

# Check health
kubectl exec -n mcp deploy/oci-mcp-gateway -- curl -s localhost:9000/mcp
```
