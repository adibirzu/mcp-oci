# MCP-OCI Observability Stack

This directory contains the complete observability stack for the MCP-OCI project, including metrics, traces, logs, and continuous profiling.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   UX App        │    │  MCP Servers    │    │  OCI Services   │
│  (Port: 8010)   │    │  (Various)      │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ OTLP/Metrics         │ OTLP/Metrics         │ SDK Traces
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  OpenTelemetry Collector                        │
│                     (Port: 4317)                               │
└─────────┬───────────────────────────────┬─────────────────────┘
          │                               │
          │ Traces                        │ Metrics
          ▼                               ▼
┌─────────────────┐              ┌─────────────────┐
│     Tempo       │              │   Prometheus    │
│  (Port: 3200)   │              │  (Port: 9090)   │
└─────────────────┘              └─────────────────┘
          │                               │
          │                               │
          ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Grafana                                 │
│                      (Port: 3000)                               │
│  • Dashboards  • Alerting  • Data Source Management           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│   Pyroscope     │ ◄─── Continuous Profiling Data
│  (Port: 4040)   │
└─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- macOS with Colima (already configured)
- jq (for testing scripts)
- curl and nc (for health checks)

### Starting the Stack

1. **Start the observability services:**
   ```bash
   ./start-observability.sh
   ```

2. **Start the MCP servers:**
   ```bash
   ../scripts/mcp-launchers/start-mcp-server.sh start all
   ```

3. **Start the UX application:**
   ```bash
   ./run-ux-local.sh
   ```

4. **Test the integration:**
   ```bash
   ./test-observability.sh
   ./test-mcp-metrics.sh
   ```

## 📊 Components

### Grafana (Port: 3000)
- **Credentials:** admin/admin
- **Purpose:** Unified observability dashboard and alerting
- **Data Sources:**
  - Prometheus (metrics) - UID: `prom`
  - Tempo (traces) - UID: `tempo`
  - Pyroscope (profiles) - UID: `pyro`

### Prometheus (Port: 9090)
- **Purpose:** Metrics collection and storage
- **Scrape Targets:**
  - UX App (`host.docker.internal:8010`)
  - MCP Servers:
    - Compute (`host.docker.internal:8001`)
    - DB (`host.docker.internal:8002`)
    - Observability (`host.docker.internal:8003`)
    - Security (`host.docker.internal:8004`)
    - Network (`host.docker.internal:8006`)
    - Blockstorage (`host.docker.internal:8007`)
    - Loadbalancer (`host.docker.internal:8008`)
    - Inventory (`host.docker.internal:8009`)
    - Agents (`host.docker.internal:8011`)
  - OTEL Collector (`otel-collector:8889`)

### Tempo (Port: 3200)
- **Purpose:** Distributed tracing storage and query
- **Features:**
  - Service maps
  - Trace-to-metrics correlation
  - TraceQL support

### Pyroscope (Port: 4040)
- **Purpose:** Continuous profiling
- **Integration:** UX app automatically sends profiling data

### OpenTelemetry Collector (Port: 4317)
- **Purpose:** Telemetry data pipeline
- **Receives:** OTLP traces and metrics
- **Exports:**
  - Traces → Tempo
  - Metrics → Prometheus

## 🔧 Configuration

### Environment Variables

The following environment variables control observability behavior:

```bash
# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
OTEL_SERVICE_NAME=mcp-ux
OTEL_SERVICE_NAMESPACE=mcp-oci

# Pyroscope
ENABLE_PYROSCOPE=true
PYROSCOPE_SERVER_ADDRESS=http://localhost:4040
PYROSCOPE_APP_NAME=mcp-ux
PYROSCOPE_SAMPLE_RATE=100

# Observability URLs
GRAFANA_URL=http://localhost:3000
PROMETHEUS_URL=http://localhost:9090
TEMPO_URL=http://localhost:3200
```

### Key Features

1. **Automatic Service Discovery:** Prometheus discovers services via static configuration
2. **Health Checks:** All services include health checks for proper startup sequencing
3. **Data Correlation:** Traces are linked to metrics and profiles
4. **Persistent Storage:** Data is persisted using Docker volumes

## 🔍 Troubleshooting

### Common Issues

1. **Pyroscope connection errors:**
   - Ensure UX app uses `localhost:4040` instead of `pyroscope:4040`
   - Check that Pyroscope container is healthy

2. **OpenTelemetry warnings:**
   - Fixed with idempotent provider initialization
   - No functional impact on telemetry collection

3. **Missing metrics in Grafana:**
   - Verify Prometheus is scraping targets successfully
   - Check OTEL Collector logs for export errors

### Debugging Commands

```bash
# Check container health
docker-compose ps

# View service logs
docker-compose logs -f [service-name]

# Test endpoint connectivity
curl http://localhost:9090/-/ready
curl http://localhost:3000/api/health
curl http://localhost:3200/ready

# Check metrics collection
curl http://localhost:9090/api/v1/targets

# Verify OTLP endpoint
nc -z localhost 4317
```

## 📈 Metrics and Dashboards

### Available Metrics

- **HTTP Requests:** `http_requests_total`, `http_request_duration_seconds`
- **MCP Tool Calls:** `mcp_tool_calls_total`, `mcp_tool_duration_seconds`
- **OpenTelemetry:** `otelcol_*` metrics from collector
- **System:** Standard Prometheus metrics

### Pre-configured Dashboards

- **MCP Overview:** `/ops/grafana/dashboards/mcp-overview.json`
  - HTTP request rates and latency
  - MCP tool call metrics
  - Duration distributions

- **MCP Servers Overview:** `/ops/grafana/dashboards/mcp-servers-overview.json`
  - Server health status across all MCP servers
  - Request rates per server
  - Tool call rates and error rates
  - Average tool execution duration
  - Top tools by usage
  - OpenTelemetry collector metrics

## 🎯 Integration with MCP Servers

Each MCP server can emit telemetry by:

1. **Importing observability utilities:**
   ```python
   from mcp_oci_common.observability import init_tracing, tool_span
   ```

2. **Initializing tracing:**
   ```python
   tracer = init_tracing("oci-mcp-compute")
   ```

3. **Instrumenting tool functions:**
   ```python
   with tool_span(tracer, "list_instances", mcp_server="oci-mcp-compute"):
       # tool implementation
   ```

## 🔄 Maintenance

### Data Retention
- **Prometheus:** 15 days (configurable)
- **Tempo:** 1 hour compacted block retention
- **Grafana:** Persistent dashboards and configurations

### Cleanup
```bash
# Stop all services and remove volumes
docker-compose down -v

# Remove all observability data
docker volume prune -f
```

---

For more details, see the individual configuration files in each service directory.