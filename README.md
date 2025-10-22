# MCP-OCI: Oracle Cloud Infrastructure MCP Servers

[![CI](https://github.com/adibirzu/mcp-oci/actions/workflows/ci.yml/badge.svg)](https://github.com/adibirzu/mcp-oci/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/adibirzu/mcp-oci/branch/main/graph/badge.svg)](https://codecov.io/gh/adibirzu/mcp-oci)

MCP-OCI provides a suite of Model Context Protocol (MCP) servers that let LLMs automate, observe, and secure Oracle Cloud Infrastructure environments. Each server is scoped to a single OCI domain and follows the OCI MCP design guidelines (deterministic behaviour, structured errors, least-privilege defaults).

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

The installer bootstraps a virtualenv, validates OCI credentials, builds the Docker image, and starts the observability stack plus all MCP servers in daemon mode.

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
- **Environment variables**: copy `.env.sample` and export values (tenancy, user OCID, key path, fingerprint)
- **Instance/resource principals**: supported automatically when running on OCI compute/containers

## Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `OCI_PROFILE` | OCI CLI profile used by SDK clients | `DEFAULT` |
| `OCI_REGION` | Target region | `us-ashburn-1` |
| `COMPARTMENT_OCID` | Default compartment scope | tenancy OCID |
| `ALLOW_MUTATIONS` | Enable write operations for mutating tools | `false` |
| `MCP_OCI_PRIVACY` | Mask OCIDs and namespaces in responses | `true` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint for traces/metrics/logs | `localhost:4317` |
| `METRICS_PORT` | Prometheus metrics port (per server) | server dependent |

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
| Observability Hub | `mcp_servers/observability` | `oci:observability:get-metrics-summary` | [docs/servers/observability.md](docs/servers/observability.md) |
| Generative AI Agents | `mcp_servers/agents` | `oci:agents:list-agents` | [docs/servers/agents.md](docs/servers/agents.md) |

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

### Observability stack

```bash
./run-all-local.sh                         # Prometheus, Tempo, Pyroscope, Grafana, UX
```

Each server publishes OTLP spans/metrics; HTTP variants also expose `/metrics`. Set `OTEL_EXPORTER_OTLP_ENDPOINT` to point at the collector (`otel-collector:4317` in Docker Compose).

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
