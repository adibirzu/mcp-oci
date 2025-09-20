# OCI MCP for OCI + Observability (Production-Ready)

## Overview
Production-ready MCP servers for Oracle Cloud Infrastructure (OCI), including a consolidated Observability server that exposes Log Analytics tools. The project follows MCP server best practices and adds in-process caching and a shared name→OCID registry to reduce API calls and token usage.

Key features:
- Single consolidated Observability server (oci-mcp-observability) with Log Analytics and observability helpers.
- Individual MCP servers for IAM, Compute, Networking, Object Storage, etc.
- Deterministic, idempotent behavior; explicit confirmation for destructive actions.
- Name→OCID registry populated by list calls; subsequent name-based requests avoid backend calls.
- Tunable cache TTLs per service; secrets are never committed (see .gitignore).

## Installation
From GitHub:
```
git clone https://github.com/<org>/<repo>.git
cd <repo>
```

Copy environment template and edit:
```
cp .env.sample .env   # then edit to set COMPARTMENT_OCID, etc.
```

Option A (one‑shot):
```
scripts/deploy.sh
```

Option B (manual):
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[dev]
make lint
make test
```

Prerequisites:
- Python 3.10+ with venv
- git
- OCI config at `~/.oci/config` with a working profile (DEFAULT by default)
- On Linux, ensure `build-essential` (or equivalent) for any native deps

## Configuration
Set OCI credentials in `~/.oci/config`. Optionally set defaults:
```
export OCI_PROFILE=DEFAULT
export OCI_REGION=eu-frankfurt-1
```

## Quickstart

### 1-Click Local Run for Observability Stack

To quickly start the observability stack (Grafana, Prometheus, Tempo, OTEL Collector, obs_app):

```
cd ops
docker compose up -d
```

This provides monitoring and tracing. Access Grafana at http://localhost:3000 (admin/admin).

### Launching MCP Servers

Run each server in a separate terminal (or use tmux/screen):

```
poetry run python mcp_servers/compute/server.py
poetry run python mcp_servers/db/server.py
poetry run python mcp_servers/network/server.py
poetry run python mcp_servers/security/server.py
poetry run python mcp_servers/observability/server.py   # Consolidated server (includes Log Analytics)
poetry run python mcp_servers/cost/server.py
poetry run python mcp_servers/blockstorage/server.py
poetry run python mcp_servers/loadbalancer/server.py
```

Alternatively, use the launcher script for all:

```
scripts/mcp-launchers/start-mcp-server.sh all
```

### One‑Shot AIOps Deploy (Web3 UX + DB)

End‑to‑end setup that provisions Autonomous JSON DB (optional), creates tables, populates data from MCP, warms caches/registry, and starts both the consolidated Observability MCP server and the Web3 UX on port 8080:

```
scripts/deploy_full_aiops.sh
```

Environment variables (examples) for DB wallet and optional Agents proxy:

- ORACLE_DB_USER=ADMIN
- ORACLE_DB_PASSWORD=ChangeMe123!
- ORACLE_DB_SERVICE=<adb_service_name>  # e.g., abcd1234_high
- ORACLE_DB_WALLET_ZIP=/path/to/Wallet_MyADB.zip
- ORACLE_DB_WALLET_PASSWORD=ChangeMe123!
- COMPARTMENT_OCID=ocid1.tenancy.oc1..xxxx  # used to scope provisioning/discovery
- GAI_AGENT_ENDPOINT=http://localhost:8088/agents/chat  # optional, Java service proxy
- GAI_AGENT_API_KEY=...  # optional

After it completes:

- Observability MCP server logs: `logs/observability.log`
- Web3 UX: http://localhost:8080 (Redwood‑styled SPA with Discovery, Relations, Costs, FinOps AI, DB Sync)
  - If 8080 is busy, set `WEB3_UX_PORT=8081 scripts/deploy_full_aiops.sh` and open http://localhost:8081

Notes:
- Works on macOS and Linux. No hard‑coded paths; Python executables are detected dynamically.
- DB features are optional. If DB envs are not set, the app still starts; DB endpoints will return guidance.
- For provisioning AJD from the script, set both `COMPARTMENT_OCID` and `ADMIN_PASSWORD`.

### Linux Prerequisites
- Python 3.10+ and venv available (`python3 -m venv`)
- Ability to create processes (for background servers)
- Network access to install pip dependencies (first run)

### Stopping services
```
kill $(cat logs/observability.pid) || true
kill $(cat logs/web3_ux.pid) || true
```

### Web3 UX Integrations
- Discovery/Capacity require a compartment OCID. Either:
  - set `COMPARTMENT_OCID` in your environment (recommended), or
  - enter a compartment OCID in the UI inputs, or
  - pass `?compartment_id=...` to the API endpoints.
- Costs/ShowUsage/ShowOCI read your `~/.oci/config` profile; set `OCI_PROFILE` and `OCI_REGION` if needed.
- If DB envs are not configured, DB endpoints will return a helpful error. Configure wallet/DSN to enable DB features.

### Troubleshooting
- Import errors in Web3 UX endpoints: ensure you launched from the repo root or via the deploy script (the app auto-adds repo `src` to `PYTHONPATH`).
- Missing compartmentId errors: set `COMPARTMENT_OCID` or supply `compartment_id` to endpoints/UI.
- Port already in use: set `WEB3_UX_PORT` when running the deploy script or starting `web3_ux/server.py`.

### First‑Run Experience (from GitHub)
- If `.env` is missing, the deploy script offers to create it interactively. Defaults include:
  - `OCI_PROFILE=DEFAULT`
  - `OCI_REGION=eu-frankfurt-1`
  - `COMPARTMENT_OCID=ocid1.compartment.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq` (you can change it)
  - `ALLOW_MUTATIONS=false`
- If the OCI CLI is not installed, the script offers to install it (`brew install oci-cli` or Oracle’s install.sh via curl).
- If `~/.oci/config` is missing, you’ll be prompted to run `oci setup config` interactively to generate it.

### Generative AI Agents (OCI mode)
- MCP server `oci-mcp-agents` uses OCI SDK for Generative AI Agents with your profile/region/compartment:
  - Set `OCI_PROFILE`, `OCI_REGION`, `COMPARTMENT_OCID` in `.env`.
  - Default `GAI_MODE=oci` (no proxy required). Tools: `list_agents`, `create_agent`, `get_agent`, `update_agent`, `delete_agent`.
- Optional legacy proxy mode: set `GAI_MODE=proxy` and configure `GAI_ADMIN_ENDPOINT`/`GAI_AGENT_ENDPOINT` (used for admin/chat REST if you already have a Java service).
- Web3 UX → Agents tab integrates with the MCP server to create/list/update/delete agents; “Test” uses proxy mode if configured.

#### Endpoints & Knowledge Bases & Data Sources
- Endpoints (OCI): `create_agent_endpoint`, `list_agent_endpoints`, `get_agent_endpoint`, `update_agent_endpoint`, `delete_agent_endpoint`.
- Knowledge Bases (OCI): `create_knowledge_base`, `list_knowledge_bases`, `get_knowledge_base`, `update_knowledge_base`, `delete_knowledge_base`.
- Data Sources (OCI): `create_data_source` (Object Storage prefixes), `list_data_sources`, `get_data_source`, `update_data_source`, `delete_data_source`.
- Web3 UX panels added for KBs, Data Sources, and Endpoints under the corresponding tabs.

### Metrics, Traces, Pyroscope
- All MCP servers initialize OpenTelemetry tracing and metrics. Many start a Prometheus metrics endpoint via `prometheus_client` with `METRICS_PORT`.
- Web3 UX also exposes Prometheus metrics (set `METRICS_PORT`, default 8012) and instruments FastAPI with OpenTelemetry.
- Optional Pyroscope profiling across servers: set `ENABLE_PYROSCOPE=true`, and configure `PYROSCOPE_SERVER_ADDRESS`, `PYROSCOPE_APP_NAME`, `PYROSCOPE_SAMPLE_RATE`.

### Adding to Claude Desktop / Cline

For Claude Desktop: Edit claude_desktop_config.json and add MCP server entries from mcp.json under "mcp_servers".

For Cline: In cline_mcp_settings.json, add:

```json
"mcp_servers": [  // paste array from mcp.json ]
```

STDIO command definitions are in mcp.json, e.g.:

```json
{
  "name": "oci-mcp-compute",
  "command": ["python", "-m", "mcp_servers.compute.server"],
  "args": [],
  "env": { "OCI_PROFILE": "${OCI_PROFILE}", "OCI_REGION": "${OCI_REGION}", "COMPARTMENT_OCID": "${COMPARTMENT_OCID}" },
  "transport": "stdio"
}
```

### Infrastructure Creation & Management

**⚠️ Safety First**: All creation operations require `ALLOW_MUTATIONS=true` environment variable.

#### Example Creation Prompts:
- "Create a VCN with CIDR 10.0.0.0/16 in my compartment"
- "Create a subnet in VCN ocid1.vcn..example with CIDR 10.0.1.0/24"
- "Launch a VM.Standard.E2.1.Micro compute instance in subnet ocid1.subnet..example"
- "Create a 100GB block volume in availability domain AD-1"
- "Set up a load balancer with listeners for my web application"

### Example Prompts for Claude

- "List my instances in compartment ocid1.compartment.oc1..example and start ocid1.instance.oc1.example"
- "Create a complete infrastructure stack: VCN, subnet, VM, and load balancer"
- "Run Log Analytics query using the oci:loganalytics:execute_query tool (auto-discovers namespace)"
- "Show Grafana dashboard and a trace in Tempo"
- "Run cost anomaly on series [100, 200, 150, 500, 180]"
- "Summarize open Cloud Guard problems in last 24h"
- "List my block volumes and create a new 50GB volume"

## Architecture & Data Flow

```mermaid
graph TD
    A[Claude/Cline] -->|MCP/STDIO| B[MCP Servers]
    B -->|OCI SDK| C[OCI APIs]
    B -->|OTel Traces/Metrics| D[OTel Collector]
    D --> E[Tempo Traces]
    D --> F[Prometheus Metrics]
    G[obs_app] -->| /metrics | F
    F --> H[Grafana Dashboards]
    E --> H
    I[UX App] -->|HTTP| H
    I -->|/metrics| F
```

## Demo Script (5-7 min flow)

1. In Claude (with MCP): Ask to list instances and start one.
2. Run a Log Analytics query (e.g., `oci:loganalytics:execute_query`) or list sources.
3. Visit UX at localhost:8000 to see servers and relations.
4. Navigate to /dashboards to view embedded Grafana.
5. In Tempo (Grafana), search for a trace from obs_app.
6. Run cost anomaly tool on a sample series.
7. Summarize Cloud Guard open problems.

## Example Workflows

### Workflow 1: Compute Management
- Prompt: "List running instances in my compartment and provide CPU metrics for the last hour."
- Expected: Uses compute list + metrics tools; outputs summary.

### Workflow 2: Security Check
- Prompt: "Scan for open Cloud Guard problems and Data Safe findings."
- Expected: Aggregates security posture.

### Workflow 3: Cost Analysis
- Prompt: "Get cost breakdown for last week and detect anomalies."
- Expected: Usage report + anomaly flags.

### Workflow 4: Log Query & Observe
- Prompt: "Run LA query for errors in last 24h; check traces in Tempo."
- Expected: Query results + navigation to traces.

Polish notes:
- All servers tested with unit tests.
- Env vars documented in .env.example.
- For production, deploy obs_app to OCI Container Instances.
## Performance & Token Optimization
- Registry: list operations populate a name→OCID registry (compartments, VCNs, subnets, instances, users, etc.). Subsequent name-based calls resolve locally without API requests.
- Caching: per-service caches with tunable TTLs (seconds):
  - Global: `MCP_CACHE_TTL` (default 3600)
  - Service overrides: `MCP_CACHE_TTL_COMPUTE`, `..._NETWORKING`, `..._IAM` (users cached 6h), `..._OKE`, `..._FUNCTIONS`, `..._STREAMING`, `..._OBJECTSTORAGE`, `..._LOADBALANCER`
- Warm helpers:
  - `mcp:warm:services` — warms global resources (compartments, users, buckets, vcns, etc.)
  - `mcp:warm:compartment` — warms a specific compartment (vcns→subnets, instances, lbs, functions, streams)
  - CLI: `scripts/warm_registry.py --profile DEFAULT --region eu-frankfurt-1 --limit 20`

## Observability helpers
- `oci:observability:get-recent-calls` — last 50 MCP calls with full path (server→tool→SDK) and success flag.
- `oci:observability:clear-recent-calls` — clear the buffer.

## Security & Secrets
- No secrets are committed. `.env` is git-ignored. SDK credentials are read from `~/.oci/config` or instance principals.
- Logging redacts sensitive info and does not echo credentials.

## Development
- Lint/format: `make lint` / `make fmt`
- Tests: `make test`
- Launch servers via `python mcp_servers/<service>/server.py` or use entries in `mcp.json`.
