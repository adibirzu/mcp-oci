# MCP-OCI: Oracle Cloud Infrastructure MCP Servers

## Important Disclaimer

All projects published under the GitHub account **adibirzu** are personal projects created and maintained independently by Adrian Birzu. They are not affiliated with, created by, or maintained by Oracle Corporation or any of its affiliates. These projects are developed to touch certain needs and do not represent official Oracle products, services, or endorsements.

[![CI](https://github.com/adibirzu/mcp-oci/actions/workflows/ci.yml/badge.svg)](https://github.com/adibirzu/mcp-oci/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/adibirzu/mcp-oci/branch/main/graph/badge.svg)](https://codecov.io/gh/adibirzu/mcp-oci)

MCP-OCI provides a suite of Model Context Protocol (MCP) servers that let LLMs automate, observe, and secure Oracle Cloud Infrastructure environments. Each server is scoped to a single OCI domain and follows the OCI MCP design guidelines (deterministic behaviour, structured errors, least-privilege defaults).

## Standards

- `docs/OCI_MCP_SERVER_STANDARD.md`

## Runbooks

- `docs/runbooks/README.md`

## Transport & Auth

- **Local development**: STDIO only
- **Production/remote**: Streamable HTTP with OAuth enabled

## Overview

- **Multi-domain coverage** – Compute, Database, Networking, Security, Cost, Observability, Load Balancing, Inventory, Block Storage, Log Analytics, and OCI Generative AI agents
- **Deterministic tools** – Stable identifiers (`oci:<service>:<action>`) with colon aliases and snake_case names
- **Observability-first** – OTLP traces/metrics, optional Prometheus endpoints, integration with the included observability stack
- **Privacy aware** – Redaction enabled by default (`MCP_OCI_PRIVACY=true`)

### Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                       LLM Client (MCP)                        │
└────────────────────────────┬──────────────────────────────────┘
                             │  MCP Protocol
┌────────────────────────────┴──────────────────────────────────┐
│                     MCP-OCI Server Suite                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │  Compute    │ │   Network   │ │  Security   │ │   Cost   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │ Block Store │ │    DB       │ │ Observability│ │ Inventory│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │
└────────────────────────────┬──────────────────────────────────┘
                             │  OCI SDK / REST
┌────────────────────────────┴──────────────────────────────────┐
│                Oracle Cloud Infrastructure Services           │
└───────────────────────────────────────────────────────────────┘
```

## Installation

### One-line install

```bash
./scripts/install.sh
```

The installer bootstraps a virtualenv, validates OCI credentials, runs tenancy discovery, builds the Docker image, and starts the observability stack plus all MCP servers in daemon mode.

### Manual setup

```bash
git clone https://github.com/adibirzu/mcp-oci.git
cd mcp-oci
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[oci]
make fmt lint test  # optional but recommended
```

### OCI configuration

- **OCI CLI config**: `oci setup config` (default `~/.oci/config`)
- **Environment variables**: Copy `.env.local.example` to `.env.local` and customize
  ```bash
  cp .env.local.example .env.local
  # Edit .env.local with your values
  ```
- **Instance/resource principals**: supported automatically when running on OCI compute/containers

**Note**: All environment variables are automatically loaded from `.env.local` (if present) before any other configuration. This file is git-ignored for security.

## Configuration

**All configuration is loaded from `.env.local` automatically.** Copy `.env.local.example` to `.env.local` and customize:

```bash
cp .env.local.example .env.local
# Edit .env.local with your values
```

### Key Configuration Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OCI_PROFILE` | OCI CLI profile used by SDK clients | `DEFAULT` |
| `OCI_REGION` | Target region | `us-ashburn-1` |
| `COMPARTMENT_OCID` | Default compartment scope | tenancy OCID |
| `ALLOW_MUTATIONS` | Enable write operations for mutating tools | `false` |
| `MCP_OCI_PRIVACY` | Mask OCIDs and namespaces in responses | `true` |
| `OCI_APM_ENDPOINT` | OCI APM OTLP endpoint (takes precedence) | - |
| `OCI_APM_PRIVATE_DATA_KEY` | Private data key for OCI APM authentication | - |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint for traces/metrics/logs | `localhost:4317` |
| `OTEL_DISABLE_LOCAL` | Disable local OTEL collector fallback | `false` |
| `METRICS_PORT` | Prometheus metrics port (per server) | server dependent |
| `MCP_CACHE_DIR` | Shared cache directory for MCP servers | `~/.mcp-oci/cache` |
| `MCP_CACHE_BACKEND` | Cache backend (`file` or `redis`) | `file` |
| `MCP_REDIS_URL` | Redis connection URL for shared cache | `redis://localhost:6379` |
| `MCP_CACHE_KEY_PREFIX` | Redis key prefix for shared cache | `mcp:cache` |

**See [Configuration Guide](docs/configuration.md) for complete documentation.**

Additional tunables are documented per server (cache TTLs, retry tuning, FinOpsAI settings, etc.).

## Tools & Resources

| Server | Package | Example tool | Doc |
|--------|---------|--------------|-----|
| Compute | `mcp_servers/compute` | `oci:compute:list-instances` | [docs/servers/compute.md](docs/servers/compute.md) |
| Database | `mcp_servers/db` | `oci:database:list-autonomous-databases` | [docs/servers/db.md](docs/servers/db.md) |
| Networking | `mcp_servers/network` | `oci:network:list-vcns` | [docs/servers/network.md](docs/servers/network.md) |
| Security | `mcp_servers/security` | `oci:security:list-iam-users` | [docs/servers/security.md](docs/servers/security.md) |
| Cost / FinOpsAI | `mcp_servers/cost` | `oci:cost:get-summary` | [docs/servers/cost.md](docs/servers/cost.md) |
| Block Storage | `mcp_servers/blockstorage` | `oci:blockstorage:list-volumes` | [docs/servers/blockstorage.md](docs/servers/blockstorage.md) |
| Load Balancer | `mcp_servers/loadbalancer` | `oci:loadbalancer:list-load-balancers` | [docs/servers/loadbalancer.md](docs/servers/loadbalancer.md) |
| Inventory | `mcp_servers/inventory` | `oci:inventory:list-resources` | [docs/servers/inventory.md](docs/servers/inventory.md) |
| Log Analytics | `mcp_servers/loganalytics` | `oci:loganalytics:execute-query` | [docs/servers/loganalytics.md](docs/servers/loganalytics.md) |
| Object Storage | `mcp_servers/objectstorage` | `oci:objectstorage:list-buckets` | [docs/servers/objectstorage.md](docs/servers/objectstorage.md) |
| Observability Hub | `mcp_servers/observability` | `oci:observability:get-metrics-summary` | [docs/servers/observability.md](docs/servers/observability.md) |
| Generative AI Agents | `mcp_servers/agents` | `oci:agents:list-agents` | [docs/servers/agents.md](docs/servers/agents.md) |
| Unified (All Tools) | `mcp_servers/unified` | `doctor` | [docs/servers/unified.md](docs/servers/unified.md) |

## Usage

### Start locally

```bash
# Launch all servers (daemon mode, writes PID files under /tmp)
scripts/mcp-launchers/start-mcp-server.sh all --daemon

# Launch a single server in the foreground
auth env vars...
scripts/mcp-launchers/start-mcp-server.sh compute

# Validate tools
python scripts/smoke_check.py
```

### `mcp-oci-serve`

Expose a single service over stdio/HTTP:

```bash
mcp-oci-serve compute --profile DEFAULT --region eu-frankfurt-1 --transport stdio
```

### Docker workflow

```bash
scripts/docker/build.sh                    # Build mcp-oci:latest (once)
OCI_PROFILE=DEFAULT OCI_REGION=eu-frankfurt-1   scripts/docker/run-server.sh compute -- --transport streamable-http
```

The helper automatically mounts the workspace and `~/.oci` for credentials. `mcp-docker.json` references the same helper so MCP clients can launch servers in containers without manual flags.

### Deploy to OCI Compute

Provision an Oracle Linux VM (VM.Standard.E6.Flex 2 OCPUs / 16 GB RAM) with Docker, firewall rules, and streamable HTTP transport pre-configured:

```bash
cd ops/terraform/mcp_streamable
./setup.sh            # gathers values from ~/.oci/config and previous runs
terraform init
terraform apply
```

Terraform creates a VCN, subnet, internet gateway, and an NSG that opens the MCP ports (7001–7011, 8000–8011) only to the source CIDR captured during setup, alongside a compute instance. If image discovery ever fails, you can set `image_id` manually in `terraform.tfvars.json`. After `apply`, SSH to the host and run the bootstrap helper to supply OCI environment values (defaults pre-filled from prior runs) and start the containers:

```bash
ssh opc@$(terraform output -raw instance_public_ip)
cd ~/mcp-oci-cloud
./bootstrap-mcp.sh
```

The bootstrap script prompts for `KEY=VALUE` pairs (e.g. `OCI_PROFILE`, `OCI_REGION`, `COMPARTMENT_OCID`), writes them to `.env.local`, enforces `MCP_TRANSPORT=streamable-http`, and starts the Docker composition exposing the MCP servers over streamable HTTP. OS firewall rules are configured automatically via cloud-init; the instance NSG is opened for the same ports.

### Observability stack

```bash
./run-all-local.sh                         # Prometheus, Tempo, Pyroscope, Grafana, UX
```

Each server publishes OTLP spans/metrics; HTTP variants also expose `/metrics`. 

**Telemetry Configuration:**
- **OCI APM (Production)**: Set `OCI_APM_ENDPOINT` and `OCI_APM_PRIVATE_DATA_KEY` to send traces directly to OCI APM
- **Local Collector (Development)**: Defaults to `localhost:4317` (otel-collector:4317 in Docker Compose)
- **Disable Local**: Set `OTEL_DISABLE_LOCAL=true` to disable local collector when using OCI APM

See [Telemetry Configuration Guide](docs/telemetry.md) for detailed setup instructions.

## Development

```bash
make setup        # create venv + install dev extras
make lint         # Ruff
make fmt          # Black
make test         # pytest (unit + integration fakes)
```

Key shared modules live under `dev/mcp-oci-x-services/` and `mcp_oci_common/`. Reuse helpers (client factory, caching, privacy, observability) rather than duplicating logic inside servers.

## Next: mcp-oci-servers

- [src/mcp_oci_compute](src/mcp_oci_compute)
- [src/mcp_oci_networking](src/mcp_oci_networking)
- [src/mcp_oci_functions](src/mcp_oci_functions)
- [src/mcp_oci_streaming](src/mcp_oci_streaming)
- [src/mcp_oci_usageapi](src/mcp_oci_usageapi)
- [src/mcp_oci_loadbalancer](src/mcp_oci_loadbalancer)

These packages contain production MCP servers published to MCP registries.

## Support & Licensing

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/adibirzu/mcp-oci/issues)
- Discussions: [GitHub Discussions](https://github.com/adibirzu/mcp-oci/discussions)

Licensed under the MIT License. See [LICENSE](LICENSE).

## Roadmap Highlights

- Additional OCI service coverage (Object Storage, Budgets, Limits)
- Observability-to-OCI integrations (Logging Analytics, Monitoring)
- Automated FinOps anomaly detection and remediation playbooks
- Multi-cloud MCP adapters (AWS, Azure, GCP)
