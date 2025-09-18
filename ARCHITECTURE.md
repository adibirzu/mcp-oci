# OCI MCP Servers - Architecture & Operations Guide

Last Updated: September 17, 2025  
Version: 2.1  
Status: Production Ready

## System Overview

The OCI MCP (Model Context Protocol) Servers provide a streamlined interface for AI clients and operator UIs to interact with Oracle Cloud Infrastructure services using FastMCP. The system is optimized for:
- Clean black-box server tools with consistent APIs
- Minimal token usage for LLM integrations (diff-first responses, slim schemas)
- Observability by default (OpenTelemetry, Prometheus, Tempo)
- Optional continuous profiling (Pyroscope)
- Safe mutation controls (ALLOW_MUTATIONS gating)

## Project Structure (Current)

```
mcp-oci/
├── mcp_servers/                    # MCP servers (FastMCP)
│   ├── compute/
│   │   └── server.py               # Start/Stop/Restart, metrics
│   ├── db/
│   │   └── server.py               # DB Systems/Autonomous DB start/stop/restart, metrics
│   ├── network/
│   │   └── server.py               # VCNs, Subnets, summaries
│   ├── security/
│   │   └── server.py               # IAM/Cloud Guard/Data Safe (read-only)
│   ├── cost/
│   │   └── server.py               # Usage API + ShowUsage integration (diff-first)
│   ├── observability/
│   │   └── server.py               # Log Analytics (basic + enhanced Logan wrappers)
│   └── inventory/
│       └── server.py               # ShowOCI integration (diff-first), env defaults
│
├── mcp_oci_common/                 # Shared utilities
│   ├── config.py                   # OCI config loading, compartment handling
│   └── observability.py            # OTEL init, span helpers, token metrics
│
├── third_party/
│   └── oci-python-sdk/examples/    # Vendored Oracle examples (showoci, showusage)
│
├── scripts/
│   ├── mcp-launchers/
│   │   └── start-mcp-server.sh     # Repo launcher (consistent env + OTEL defaults)
│   └── vendor_oracle_examples.sh   # Vendor showoci/showusage into third_party/
│
├── ux/
│   ├── app.py                      # Operator UI (FastAPI) on port 8000
│   └── templates/                  # Pages (diagram, dashboards)
│
├── ops/
│   └── grafana/dashboards/
│       ├── mcp-insights.json       # Tempo trace insights (TraceQL)
│       └── mcp-monitoring.json     # Tempo + Prometheus monitoring overview
│
├── mcp.json                        # Local MCP server definitions for clients
├── ARCHITECTURE.md                 # This document
└── README.md
```

Notes:
- Legacy src/mcp_oci_fastmcp* packages and docs are kept for reference, but the current servers used by mcp.json live under mcp_servers/.
- Enhanced Log Analytics (Logan) features are bridged via wrappers in mcp_servers/observability/server.py.

## Server Design

Each MCP server follows a consistent pattern:
- FastMCP app with tools defined via Tool.from_function(...)
- OpenTelemetry tracing and metrics exported via OTLP (gRPC) to collector
- Optional /metrics (Prometheus) exposure in DEBUG mode with unique port
- Optional Pyroscope continuous profiling (safe, opt-in)
- Resilient FastAPI instrumentation (instrument_app over mcp.app or mcp.fastapi_app; fallback to global instrument())

Example (Compute):
- list_instances(compartment_id?, region?, lifecycle_state?)
- start_instance(instance_id)
- stop_instance(instance_id)
- restart_instance(instance_id, hard=False)  # SOFTRESET default; RESET when hard=True
- get_instance_metrics(instance_id, window="1h")

Database:
- DB Systems: start_db_system, stop_db_system, restart_db_system
- Autonomous DB: start_autonomous_database, stop_autonomous_database, restart_autonomous_database
- get_db_cpu_snapshot(db_id, window="1h")

Inventory (ShowOCI):
- run_showoci(profile?, regions?, compartments?, resource_types?, output_format="text", diff_mode=True, limit?)
- run_showoci_simple(profile?, regions="r1,r2", compartments="c1,c2", ...)  # convenience wrapper
- Caches outputs under /tmp/mcp-oci-cache/inventory keyed by parameters; returns unified diff when diff_mode=True

Cost (Usage API + ShowUsage):
- get_cost_summary(time_window="7d", granularity="DAILY", ...)
- get_usage_breakdown(service?, ...)
- detect_cost_anomaly(series, method?)
- detect_budget_drift(budget_amount, ...)
- run_showusage(profile?, time_range?, granularity="DAILY", service_filters?, compartment_id?, output_format="text", diff_mode=True, limit?)
- Caches under /tmp/mcp-oci-cache/cost; returns diff when diff_mode=True

Security:
- Read-only IAM/Cloud Guard/Data Safe tools

Observability:
- Basic LA tools + enhanced Logan wrappers (execute_logan_query, search_security_events, get_mitre_techniques, etc.)

## Communication & Data Flow

High-level:
```
AI Client / UX ---- FastMCP Tool Call ----> MCP Server
MCP Server ---------> OCI SDK API --------> OCI Backend
MCP Server -----> OTEL (spans/metrics) ---> Collector -> Tempo/Prometheus
MCP Server -----> Pyroscope (optional) ----> Pyroscope server
```

Operator UX (port 8000):
- Renders a unified relations diagram (Mermaid) by introspecting mcp.json and importing server modules for tool schemas
- Shows all servers including oci-mcp-inventory (ShowOCI) with available tools
- Exposes /metrics (Prometheus)

Per-server landing (FastMCP):
- Each MCP server may have its own “landing page” (e.g., on an internal port) with framework defaults, but the authoritative unified diagram is the UX app at port 8000.

## Observability

OpenTelemetry:
- Traces: OTLP gRPC to collector (Tempo)
- Metrics: OTLP gRPC to collector (Prometheus via OTEL Collector)
- Endpoint normalization: observability._normalize_otlp_endpoint(...) ensures gRPC exporter receives host:port (scheme-less), preventing “only mcp-ux” traces

Span attributes:
- mcp.server.name, mcp.tool.name for grouping
- oci.service, oci.operation, oci.region, oci.endpoint for backend call attribution
- Token usage:
  - Counter metric: oci.mcp.tokens.total
  - Span attributes: oci.mcp.tokens.total/request/response
  - Implemented in mcp_oci_common/observability.py and used by inventory/cost (based on text size for minimal overhead)

Prometheus:
- UX app exposes /metrics
- Servers can expose /metrics in DEBUG mode on unique ports to avoid conflicts

Grafana Dashboards:
- ops/grafana/dashboards/mcp-insights.json (TraceQL: server/tool breakdowns)
- ops/grafana/dashboards/mcp-monitoring.json (Tempo + Prometheus: traffic, errors, UX HTTP rate, p95 latency, recent spans)

Pyroscope (optional):
- All servers include opt-in Pyroscope profiling guarded by env:
  - ENABLE_PYROSCOPE=true
  - PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040
  - PYROSCOPE_APP_NAME defaults to service name (e.g., oci-mcp-compute)
  - PYROSCOPE_SAMPLE_RATE default 100 Hz
- Safe fallback: profiling disabled if library not installed

## Token Optimization Strategy

- Diff-first outputs for ShowOCI/ShowUsage (send only changes when possible)
- Minimal schemas tailored for LLM consumption
- Token usage metrics recorded in spans and via a counter for future budgeting/alerting

## Configuration

Environment:
- OCI_PROFILE, OCI_REGION, COMPARTMENT_OCID
- ALLOW_MUTATIONS=true    # to enable start/stop/restart tools
- OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 (normalized to gRPC host:port)
- ENABLE_PYROSCOPE=true (opt-in)
- PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040

mcp.json (clients):
- Defines how clients launch servers:
```
[
  { "name": "oci-mcp-compute", "command": ["python", "-m", "mcp_servers.compute.server"], ... },
  { "name": "oci-mcp-db", ... },
  { "name": "oci-mcp-network", ... },
  { "name": "oci-mcp-security", ... },
  { "name": "oci-mcp-observability", ... },
  { "name": "oci-mcp-cost", ... },
  { "name": "oci-mcp-inventory", ... }
]
```

Repo Launcher:
- scripts/mcp-launchers/start-mcp-server.sh
  - Ensures project root, sets PYTHONPATH to include src/, and starts the selected server module

External Launcher Schema Compatibility:
- Some external environments expect to cd into:
  - /Users/abirzu/dev/mcp-oci-<service>-server
- To align without changing external scripts, create symlinks to the repo root:
  - /Users/abirzu/dev/mcp-oci-compute-server -> /Users/abirzu/dev/mcp-oci
  - /Users/abirzu/dev/mcp-oci-db-server -> /Users/abirzu/dev/mcp-oci
  - /Users/abirzu/dev/mcp-oci-network-server -> /Users/abirzu/dev/mcp-oci
  - /Users/abirzu/dev/mcp-oci-security-server -> /Users/abirzu/dev/mcp-oci
  - /Users/abirzu/dev/mcp-oci-observability-server -> /Users/abirzu/dev/mcp-oci
  - /Users/abirzu/dev/mcp-oci-cost-server -> /Users/abirzu/dev/mcp-oci
  - /Users/abirzu/dev/mcp-oci-inventory-server -> /Users/abirzu/dev/mcp-oci
- This resolves “cd: /Users/abirzu/dev/mcp-oci-<svc>-server: No such file or directory” errors in external launcher scripts

## Communication Flow (Detailed)

Mermaid (UX-level aggregate):
```mermaid
graph TD
  A[AI Client / UX] -->|MCP| B[oci-mcp-*-server]
  B -->|OTEL| C[OTLP Collector]
  C -->|Traces| D[Tempo]
  C -->|Metrics| E[Prometheus]
  B -->|Pyroscope (opt)| F[Pyroscope]
  B -->|SDK| G[OCI APIs]
  G --> H[OCIServices]
```

Span semantics:
- mcp.server.name = "oci-mcp-<service>"
- mcp.tool.name = the tool function name
- oci.service + oci.operation denote backend call intent (e.g., Compute/ListInstances)

## Operations

Local run (repo launcher):
```
./scripts/mcp-launchers/start-mcp-server.sh compute
./scripts/mcp-launchers/start-mcp-server.sh cost
./scripts/mcp-launchers/start-mcp-server.sh all
```

External launcher compatibility:
- Ensure symlinks for /Users/abirzu/dev/mcp-oci-<service>-server exist, pointing to /Users/abirzu/dev/mcp-oci

Profiling + Observability:
```
export ENABLE_PYROSCOPE=true
export PYROSCOPE_SERVER_ADDRESS=http://localhost:4040
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
# Optional service metadata
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=local,service.namespace=mcp-oci,service.version=dev"
```

Vendoring Oracle examples:
```
# Clone OCI SDK to repo (or reuse local path)
git clone https://github.com/oracle/oci-python-sdk.git oci-python-sdk
ORACLE_SDK_PATH=oci-python-sdk ./scripts/vendor_oracle_examples.sh
# Adds: third_party/oci-python-sdk/examples/showoci, showusage
```

## Safety & Mutations

- All mutation tools (start/stop/restart) are gated by ALLOW_MUTATIONS=true to prevent accidental changes
- Read-only servers (network/security) remain non-destructive

## Testing

- Unit and integration tests live under tests/
- Use pytest for local runs, mock OCI where necessary

## Change Log (Highlights)

2.1 (2025-09-17)
- Added oci-mcp-inventory server (ShowOCI), diff-first responses, env defaults
- Added ShowUsage to cost server with diff-first responses
- Restored detect_budget_drift tool in cost
- Added restart_instance to compute (SOFTRESET/RESET)
- Added DB Systems/Autonomous DB start/stop/restart
- Token usage telemetry added (counter + span attributes)
- Normalized OTLP exporter endpoint handling for gRPC
- Added optional Pyroscope profiling to all servers
- Added Grafana mcp-monitoring.json (Tempo + Prometheus)
- Documentation updated to current structure and flows

2.0 (2025-09-15)
- Project marked Production Ready
- FastMCP optimizations and documentation complete

## Support

- See docs/ for server-specific guides
- Open issues in the repository for bugs/requests
- OCI Support for tenant-specific issues
