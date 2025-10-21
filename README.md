# MCP-OCI: Oracle Cloud Infrastructure MCP Servers

[![CI](https://github.com/adibirzu/mcp-oci/actions/workflows/ci.yml/badge.svg)](https://github.com/adibirzu/mcp-oci/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/adibirzu/mcp-oci/branch/main/graph/badge.svg)](https://codecov.io/gh/adibirzu/mcp-oci)

A comprehensive suite of Model Context Protocol (MCP) servers for Oracle Cloud Infrastructure, providing AI-powered cloud operations, cost analysis, and observability.

## 🌟 Overview

MCP-OCI is a collection of specialized MCP servers that enable Large Language Models (LLMs) to interact with Oracle Cloud Infrastructure services. Each server focuses on specific OCI domains, providing tools for automation, analysis, and monitoring.

### Key Features

- 🔧 **Multi-Domain Coverage**: 11+ specialized MCP servers covering compute, networking, security, cost analysis, and more
- 📊 **Advanced Analytics**: AI-powered cost optimization, trend analysis, and anomaly detection
- 🔍 **Comprehensive Observability**: Full-stack monitoring with Grafana, Prometheus, Tempo, and Pyroscope
- 🛡️ **Security-First**: Built-in security scanning, vulnerability assessment, and compliance checking
- 🚀 **Cloud-Native**: Containerized deployment with Docker and Kubernetes support
- 📈 **FinOps Integration**: Advanced financial operations with cost forecasting and budget management

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         LLM Client (MCP)                        │
└─────────────────────────────┬───────────────────────────────────┘
                              │ MCP Protocol
┌─────────────────────────────┴───────────────────────────────────┐
│                    MCP-OCI Server Suite                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │   Compute   │ │  Networking │ │  Security   │ │    Cost     ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │ Block Store │ │     DB      │ │ Observ.     │ │ Inventory   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────┬───────────────────────────────────┘
                              │ OCI SDK
┌─────────────────────────────┴───────────────────────────────────┐
│                Oracle Cloud Infrastructure                      │
│     Compute • Network • Security • Storage • Database         │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### One-line install (recommended)

Prerequisites are handled automatically by the installer (Python venv, OCI CLI via pip if missing, Docker/Compose check, Docker image build). It will verify your OCI configuration and only then start the Observability stack and MCP servers.

```bash
# From the repository root
./scripts/install.sh
```

What the installer does:
- Checks/Guides Docker and Docker Compose availability
- Creates and populates a Python virtualenv; installs project deps with [oci] extras
- Installs OCI CLI via pip if it's not found on your system
- Verifies OCI config (uses ~/.oci/config or proceeds if environment credentials/instance principals are present)
- Builds the local Docker image mcp-oci:latest
- Starts the Observability stack (Grafana, Prometheus, Tempo, Pyroscope, OTEL Collector) using docker compose
- Starts all MCP servers via the unified launcher and writes a health summary to ops/MCP_HEALTH.json

If no OCI config is found, the installer will stop and instruct you to run:
```bash
source .venv/bin/activate
oci setup config
```
After which you can re-run:
```bash
./scripts/install.sh
```

Alternate MCP configuration:

### Prerequisites

- Python 3.11+
- Oracle Cloud Infrastructure account and CLI configuration
- Docker (for observability stack)
- Git

### 1. Linux Installation (recommended)

Prerequisites
- A Linux host with internet access
- Python 3.11+ and Git installed
- OCI credentials configured (either ~/.oci/config or Instance Principal)

Steps
```bash
# 1) Clone and enter repo
git clone https://github.com/adibirzu/mcp-oci.git
cd mcp-oci

# 2) Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[oci]

# 3) Verify CLI and OCI access
mcp-oci doctor --profile DEFAULT --region eu-frankfurt-1

# 3) Set OCI defaults (or rely on ~/.oci/config profile DEFAULT)
export OCI_PROFILE=DEFAULT
export OCI_REGION=eu-frankfurt-1

# 4) Start all MCP servers (daemon mode)
scripts/mcp-launchers/start-mcp-server.sh all --daemon

# 5) Verify
python scripts/smoke_check.py
```

Notes
- Privacy masking is enabled by default: `MCP_OCI_PRIVACY=true`. Disable via `export MCP_OCI_PRIVACY=false` if needed.
- To stop servers: `scripts/mcp-launchers/start-mcp-server.sh stop all`
- To check status: `scripts/mcp-launchers/start-mcp-server.sh status <server>`

### 2. Installation (macOS/other)

```bash
# Clone the repository
git clone https://github.com/adibirzu/mcp-oci.git
cd mcp-oci

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies and expose CLIs
pip install -e .[oci]

# Quick doctor check
mcp-oci doctor --profile DEFAULT --region eu-frankfurt-1
```

### OCI Configuration

Set up your OCI credentials using one of these methods:

#### Option A: OCI CLI Configuration
```bash
# Install and configure OCI CLI
pip install oci-cli
oci setup config

# Your credentials will be stored in ~/.oci/config
```

#### Option B: Environment Variables
```bash
# Copy and edit environment template
cp .env.sample .env
# Edit .env with your OCI details
```

#### Option C: Resource Principal (for OCI Compute)
When running on OCI compute instances, the servers automatically use Resource Principal authentication.

### Quick Start (manual)

```bash
# Start all MCP servers
scripts/mcp-launchers/start-mcp-server.sh all --daemon

# Test that everything is working
python scripts/smoke_check.py

# Access the UX dashboard at http://localhost:8010
```

## 📦 Available MCP Servers

| Server | Description | Port | Status | Key Features |
|--------|-------------|------|--------|--------------|
| **compute** | VM and container management | 8001 | ✅ Active | Instance lifecycle, scaling, monitoring |
| **network** | Networking and connectivity | 8006 | ✅ Active | VCNs, subnets, load balancers, security |
| **security** | Security and compliance | 8004 | ✅ Active | Vulnerability scanning, policy analysis |
| **cost** | Financial operations | 8005 | ✅ Active | Cost analysis, forecasting, optimization |
| **db** | Database operations | 8002 | ✅ Active | Autonomous DB, MySQL, PostgreSQL |
| **blockstorage** | Storage management | 8007 | ✅ Active | Block volumes, backups, lifecycle |
| **observability** | Monitoring and metrics | 8003 | ✅ Active | APM, logging, alerting integration |
| **inventory** | Asset discovery | 8009 | ✅ Active | Resource discovery, tagging, compliance |
| **loadbalancer** | Load balancing | 8008 | ✅ Active | LB configuration, SSL, health checks |
| **loganalytics** | Log analytics & search | 8003 | ✅ Active | Log analysis, search, anomaly detection |
| **agents** | AI agents integration | 8011 | ✅ Active | OCI GenAI agents, chat proxies |

## 🔧 Individual Server Usage

### Running Single Servers

Serve any OCI service over stdio using the unified CLI:

```bash
# Compute
mcp-oci-serve compute --profile DEFAULT --region eu-frankfurt-1

# Object Storage
mcp-oci-serve objectstorage --profile DEFAULT --region eu-frankfurt-1

# IAM
mcp-oci-serve iam --profile DEFAULT --region eu-frankfurt-1

Note on tool names
- Tools are published with stable snake_case names (e.g., `oci_objectstorage_list_buckets`).
- For compatibility with design guidelines, colon-form aliases are also exposed automatically (e.g., `oci:objectstorage:list-buckets`).
```

### MCP Configuration

Add servers to your MCP client configuration:

#### MCP Client Configuration
```json
{
  "mcpServers": {
    "oci-compute": {
      "command": "mcp-oci-serve",
      "args": ["compute", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    },
    "oci-objectstorage": {
      "command": "mcp-oci-serve",
      "args": ["objectstorage", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    }
  }
}
```

#### Environment Variables per Server
```bash
# Compute server
export OCI_REGION=us-ashburn-1
export COMPARTMENT_OCID=ocid1.compartment.oc1..example
export ALLOW_MUTATIONS=true
export METRICS_PORT=8001

# Cost server
export FINOPSAI_CACHE_TTL_SECONDS=600
export TENANCY_OCID=ocid1.tenancy.oc1..example
```

## 📊 Observability

- All servers include observability hooks (OTLP traces/metrics). For stdio servers, send OTLP to a collector by setting `OTEL_EXPORTER_OTLP_ENDPOINT` (e.g., `http://localhost:4317`).
- Privacy masking: enable with `MCP_OCI_PRIVACY=true`. Masks OCIDs/namespaces across outputs.

## 📊 Observability Stack

MCP-OCI includes a complete observability stack with metrics, tracing, and profiling.

### Setup Observability

```bash
# Quick start - all components
./run-all-local.sh

# Or start components individually:
cd ops

# Start observability stack (Grafana, Prometheus, Tempo, Pyroscope)
./restart_observability_stack.sh

# Start all MCP servers with metrics
../scripts/mcp-launchers/start-mcp-server.sh all --daemon

# Start UX application
./run-ux-local.sh

# Test the complete stack
python ../test_observability_e2e.py
```

### Access Dashboards

- **Grafana**: http://localhost:3000 (admin/admin) - Dashboards and visualization
- **Prometheus**: http://localhost:9090 - Metrics collection and querying
- **Tempo**: http://localhost:3200 - Distributed tracing
- **Pyroscope**: http://localhost:4040 - Continuous profiling
- **Jaeger**: http://localhost:16686 - Trace exploration and analysis
- **UX Overview**: http://localhost:8010 - MCP servers status and control panel

### OCI Observability Integration

#### Option 1: OCI Monitoring Integration

```bash
# Configure OCI Monitoring
export OCI_MONITORING_NAMESPACE=mcp-oci
export OCI_MONITORING_COMPARTMENT_ID=ocid1.compartment.oc1..example

# Enable OCI metrics export
export OTEL_EXPORTER_OCI_ENABLED=true
export OTEL_EXPORTER_OCI_ENDPOINT=https://telemetry-ingestion.us-ashburn-1.oraclecloud.com
```

#### Option 2: OCI Logging Analytics

```bash
# Configure Logging Analytics
export OCI_LOG_ANALYTICS_NAMESPACE=mcp-oci
export OCI_LOG_ANALYTICS_LOG_GROUP_ID=ocid1.loggroup.oc1..example

# Enable log export
export OTEL_EXPORTER_LOGGING_ENABLED=true
```

#### Option 3: OCI APM

```bash
# Configure Application Performance Monitoring
export OCI_APM_DOMAIN_ID=ocid1.apmdomain.oc1..example
export OCI_APM_PRIVATE_DATA_KEY=your-private-data-key
export OCI_APM_PUBLIC_DATA_KEY=your-public-data-key

# Enable APM tracing
export OTEL_EXPORTER_APM_ENABLED=true
```

### Metrics Collection

- HTTP servers export a `/metrics` endpoint for Prometheus.
- Stdio servers export metrics via OTLP. Point them at your collector with `OTEL_EXPORTER_OTLP_ENDPOINT`.
  Example: `export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`

## 🛠️ Configuration

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `OCI_REGION` | OCI region | `us-ashburn-1` | `eu-frankfurt-1` |
| `OCI_PROFILE` | OCI config profile | `DEFAULT` | `my-profile` |
| `COMPARTMENT_OCID` | Default compartment | - | `ocid1.compartment.oc1..` |
| `ALLOW_MUTATIONS` | Enable write operations | `false` | `true` |
| `METRICS_PORT` | Prometheus metrics port | Server-specific | `8001` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry endpoint | `localhost:4317` | Custom endpoint |
| `MCP_OCI_PRIVACY` | Redact OCIDs/namespaces in outputs | `false` | `true` |

### Advanced Configuration

#### Cost Server (FinOps)
```bash
export FINOPSAI_CACHE_TTL_SECONDS=600
export TENANCY_OCID=ocid1.tenancy.oc1..example
export OCI_BILLING_NAMESPACE=oci_billing
```

#### Security Server
```bash
export SECURITY_SCAN_ENABLED=true
export VULNERABILITY_DB_PATH=/path/to/vuln-db
export COMPLIANCE_FRAMEWORKS=PCI,SOX,GDPR
```

#### Observability Stack
```bash
export GRAFANA_ADMIN_PASSWORD=secure-password
export PROMETHEUS_RETENTION=30d
export TEMPO_RETENTION=7d
export PYROSCOPE_STORAGE_PATH=/data/pyroscope
```

## ⚡ Performance Tunables

Client reuse and resilient I/O are enabled by default. You can tune behavior with the following environment variables:

General OCI SDK (applies to all servers via shared client factory)
- OCI_ENABLE_RETRIES=true|false (default true) — enable OCI SDK retry strategy when available
- OCI_REQUEST_TIMEOUT=seconds — set both connect/read timeouts (float seconds)
- OCI_REQUEST_TIMEOUT_CONNECT=seconds, OCI_REQUEST_TIMEOUT_READ=seconds — fine-grained timeouts

Caching (shared disk+memory cache used by servers where applicable)
- MCP_CACHE_DIR=/tmp/mcp-oci-cache (default)
- MCP_CACHE_TTL=3600 — default TTL seconds for cache entries

Log Analytics REST (applies to oci-mcp-loganalytics and wrappers)
- LA_HTTP_POOL=16 — HTTP connection pool size
- LA_HTTP_RETRIES=3 — automatic retries on 429/5xx
- LA_HTTP_BACKOFF=0.2 — seconds backoff factor for retries
- LA_HTTP_TIMEOUT=60 — per-request timeout in seconds

Networking REST (applies to create_vcn_with_subnets_rest)
- NET_HTTP_POOL=16 — HTTP connection pool size
- NET_HTTP_RETRIES=3 — automatic retries on 429/5xx
- NET_HTTP_BACKOFF=0.2 — seconds backoff factor for retries

Notes
- All servers reuse OCI SDK clients per (client class, profile, region) to reduce cold start and TLS overheads.
- If a specific SDK client does not accept retry_strategy/timeout kwargs, the factory falls back gracefully.
- Defaults are production-safe; increase *_HTTP_POOL for high concurrency workloads.

## 🔐 Security & Compliance

### Authentication Methods

1. **OCI CLI Configuration** (Development)
2. **Resource Principal** (Production on OCI)
3. **Instance Principal** (OCI Compute instances)
4. **Environment Variables** (Containerized deployments)

### Security Best Practices

- Never commit real credentials to version control
- Use Resource Principals in production
- Enable audit logging for all operations
- Regularly rotate access keys
- Monitor and alert on unusual access patterns
- Use least-privilege IAM policies

### IAM Policies Required

```hcl
# Minimum required policies
Allow group mcp-users to inspect all-resources in compartment id <compartment-ocid>
Allow group mcp-users to read all-resources in compartment id <compartment-ocid>

# For write operations (when ALLOW_MUTATIONS=true)
Allow group mcp-users to manage instances in compartment id <compartment-ocid>
Allow group mcp-users to manage volumes in compartment id <compartment-ocid>

# For cost analysis
Allow group mcp-users to read usage-report in tenancy
Allow group mcp-users to read budgets in tenancy
```

## 🧪 Testing

### End-to-End Observability Test
```bash
# Test complete observability pipeline
python test_observability_e2e.py

# Generate test metrics and traces
cd ops && python generate_test_data.py --mode all
```

### Individual Server Tests
```bash
# Test specific server functionality
python -m mcp_servers.compute.server  # Start in test mode

# Check server health and metrics
curl http://localhost:8001/metrics    # Compute server metrics
curl http://localhost:8004/metrics    # Security server metrics
```

### Integration Tests
```bash
# Test with OCI credentials (requires setup)
scripts/test_integration_frankfurt.sh
```

## 🚀 Deployment

### Local Development
```bash
# Start all components (observability + MCP servers + UX)
./run-all-local.sh

# Start individual MCP server for development
scripts/mcp-launchers/start-mcp-server.sh compute --daemon

# Stop all MCP servers
scripts/mcp-launchers/start-mcp-server.sh stop all

# Check server status
scripts/mcp-launchers/start-mcp-server.sh status compute
```

### Container Deployment
```bash
# Start observability stack with containers
cd ops
docker-compose up -d

# Check container status
docker-compose ps

# View logs
docker-compose logs -f grafana

# Stop containers
docker-compose down
```

## 📚 Advanced Usage

### Custom Tool Development

Create custom tools for specific use cases:

```python
from fastmcp import FastMCP
from fastmcp.tools import Tool

app = FastMCP("my-custom-server")

@app.tool("my_custom_operation")
def my_operation(param1: str, param2: int = 10) -> dict:
    """Custom OCI operation"""
    # Your implementation
    return {"result": "success"}

if __name__ == "__main__":
    app.run()
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes and add tests
4. Run the test suite: `python -m pytest`
5. Commit your changes: `git commit -am 'Add my feature'`
6. Push to the branch: `git push origin feature/my-feature`
7. Submit a pull request

### Development Setup

```bash
# Bootstrap and test
make setup
make test
make lint
make fmt

# Note: vendored SDK sources under oci-python-sdk/ are ignored by pytest.
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [Full documentation](docs/)
- **Issues**: [GitHub Issues](https://github.com/adibirzu/mcp-oci/issues)
- **Discussions**: [GitHub Discussions](https://github.com/adibirzu/mcp-oci/discussions)

## 🗺️ Roadmap

- [ ] Additional OCI services integration
- [ ] Multi-cloud support (AWS, Azure, GCP)
- [ ] Advanced AI-powered automation
- [ ] GraphQL API interface
- [ ] Mobile dashboard application
- [ ] Enterprise SSO integration
- [ ] Advanced compliance reporting
- [ ] Machine learning model deployment tools

---

**Made with ❤️ for the Oracle Cloud community**
