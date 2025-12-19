# MCP-OCI Observability Setup

This document explains the observability stack for MCP-OCI and how to troubleshoot common issues.

## Architecture

```
MCP Servers (Host)              Observability Stack (Docker)
  ┌─────────────┐                 ┌──────────────────┐
  │ Cost Server │─────metrics─────▶│ otel-collector  │
  │ Network Svr │─────traces──────▶│   :4317 (gRPC)  │
  │ Compute Svr │                 │   :4319 (HTTP)  │
  └─────────────┘                 └──────┬───────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
            ┌──────────────┐     ┌──────────┐       ┌──────────┐
            │  Prometheus  │     │  Tempo   │       │  Jaeger  │
            │    :9090     │     │  :3200   │       │  :16686  │
            └──────────────┘     └──────────┘       └──────────┘
                    │                    │                    │
                    └────────────────────┴────────────────────┘
                                         │
                                         ▼
                                  ┌──────────┐
                                  │ Grafana  │
                                  │  :3000   │
                                  └──────────┘
```

## Components

### 1. OpenTelemetry Collector (otel-collector)
- **Purpose**: Central collection point for metrics and traces
- **Ports**:
  - `4317`: OTLP gRPC receiver (exposed to host)
  - `4319`: OTLP HTTP receiver (mapped from container's 4318)
  - `8889`: Prometheus metrics exporter
- **Config**: `ops/otel/otel-collector.yaml`

### 2. Prometheus
- **Purpose**: Time-series database for metrics
- **Port**: `9090`
- **Scrapes**: otel-collector's Prometheus exporter at `:8889`

### 3. Tempo
- **Purpose**: Distributed tracing backend
- **Ports**:
  - `3200`: HTTP API
  - `4318`: OTLP HTTP receiver (direct)
- **Config**: `ops/tempo/tempo.yaml`

### 4. Jaeger
- **Purpose**: Trace visualization UI
- **Ports**:
  - `16686`: Jaeger UI
  - `14317`: OTLP gRPC receiver (mapped from 4317)
  - `14318`: OTLP HTTP receiver (mapped from 4318)
- **Access**: http://localhost:16686

### 5. Grafana
- **Purpose**: Observability dashboard
- **Port**: `3000`
- **Credentials**: admin/admin
- **Access**: http://localhost:3000

## Configuration

### Environment Variables

MCP servers use these environment variables (configured in `.env.local`):

```bash
# OpenTelemetry endpoint (no http:// prefix for gRPC)
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317

# Service name (optional, each server sets its own)
OTEL_SERVICE_NAME=oci-mcp-cost

# Pyroscope profiling (optional)
ENABLE_PYROSCOPE=true
PYROSCOPE_SERVER_ADDRESS=http://127.0.0.1:4040
```

### How MCP Servers Send Telemetry

MCP servers use `mcp_oci_common/observability.py` which:

1. **Initializes tracing** with `init_tracing(service_name="oci-mcp-cost")`
2. **Initializes metrics** with `init_metrics()`
3. **Creates spans** for each tool call using the `tool_span` context manager
4. **Exports to** the OTLP gRPC endpoint at `localhost:4317`

The exporter automatically:
- Strips `http://` prefix from endpoints (gRPC doesn't use HTTP scheme)
- Batches spans for efficiency
- Retries on transient failures

## Common Issues and Solutions

### Issue 1: "Failed to export metrics to localhost:4317, error code: StatusCode.UNAVAILABLE"

**Cause**: MCP servers running on host cannot reach otel-collector in Docker

**Solution**:
1. Ensure otel-collector is running: `docker ps | grep otel-collector`
2. Check port 4317 is exposed: Should show `0.0.0.0:4317->4317/tcp`
3. Verify endpoint in `.env.local` has no `http://` prefix: `OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317`
4. Restart MCP servers to pick up new environment variables

### Issue 2: otel-collector shows "unhealthy" status

**Cause**: Health check failing or backend connectivity issues

**Check logs**:
```bash
docker logs otel-collector --tail 50
```

**Common causes**:
- Tempo/Jaeger not responding (check their logs)
- Configuration errors in `otel-collector.yaml`
- Network issues in Docker

**Solution**:
```bash
cd ops
docker-compose restart otel-collector
```

### Issue 3: No traces appearing in Jaeger/Tempo

**Debugging steps**:

1. **Verify MCP server is sending traces**:
   ```bash
   # Check if server is using observability
   grep -r "init_tracing" mcp_servers/cost/server.py
   ```

2. **Check otel-collector is receiving**:
   ```bash
   docker logs otel-collector | grep -i "trace"
   ```

3. **Verify Prometheus metrics**:
   ```bash
   curl http://localhost:8889/metrics | grep otelcol_receiver
   ```

4. **Check Tempo is receiving**:
   ```bash
   curl http://localhost:3200/api/echo
   ```

### Issue 4: Port conflicts (4318 already in use)

**Cause**: Both Tempo and otel-collector want to use port 4318

**Solution**: We map otel-collector's HTTP port to 4319 on the host:
- Tempo: `4318:4318` (direct OTLP HTTP)
- otel-collector: `4319:4318` (mapped to avoid conflict)

## Starting the Observability Stack

### Option 1: Start everything
```bash
cd ops
docker-compose up -d
```

### Option 2: Start only observability (no obs-app)
```bash
cd ops
docker-compose up -d grafana prometheus tempo jaeger otel-collector
```

### Check status
```bash
docker-compose ps
```

## Accessing the UIs

- **Grafana**: http://localhost:3000 (admin/admin)
- **Jaeger**: http://localhost:16686
- **Prometheus**: http://localhost:9090
- **Tempo**: http://localhost:3200/api/echo (health check)

## Querying Traces

### In Jaeger
1. Go to http://localhost:16686
2. Select service: `oci-mcp-cost`, `oci-mcp-network`, etc.
3. Click "Find Traces"

### In Grafana
1. Go to http://localhost:3000
2. Navigate to "Explore"
3. Select "Tempo" datasource
4. Use TraceQL queries like:
   ```
   { mcp.server.name="oci-mcp-cost" }
   { mcp.tool.name="get_cost_summary" }
   { oci.service="UsageApi" && oci.operation="RequestSummarizedUsages" }
   ```

## Metrics

### Prometheus Metrics
MCP servers export these metrics via the otel-collector:

- `mcp_tool_calls_total{server, tool, outcome}` - Total tool invocations
- `mcp_tool_duration_seconds{server, tool}` - Tool execution time histogram
- `oci_mcp_tokens_total` - Token usage (future LLM integration)

### Querying in Prometheus
```promql
# Tool call rate
rate(mcp_tool_calls_total[5m])

# Average tool duration
rate(mcp_tool_duration_seconds_sum[5m]) / rate(mcp_tool_duration_seconds_count[5m])

# Error rate
rate(mcp_tool_calls_total{outcome="error"}[5m])
```

## Advanced Configuration

### Changing OTLP Endpoint

To send telemetry to a different collector:

```bash
# In .env.local
OTEL_EXPORTER_OTLP_ENDPOINT=my-collector.example.com:4317
```

### Per-Server Configuration

Each MCP server can override the endpoint:

```python
# In server.py
import os
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "custom-endpoint:4317"
init_tracing(service_name="my-custom-service")
```

### Disabling Observability

To run without telemetry:

1. Don't install observability dependencies:
   ```bash
   pip install mcp-oci  # without [observability]
   ```

2. Or unset the endpoint:
   ```bash
   unset OTEL_EXPORTER_OTLP_ENDPOINT
   ```

The code gracefully handles missing dependencies with warnings.

## Troubleshooting Checklist

- [ ] otel-collector is running and healthy
- [ ] Port 4317 is accessible from host: `curl -v http://localhost:4317`
- [ ] `.env.local` has `OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317` (no http://)
- [ ] MCP servers are restarted after changing `.env.local`
- [ ] Prometheus is scraping otel-collector: http://localhost:9090/targets
- [ ] Tempo/Jaeger are receiving traces: check their logs

## References

- [OpenTelemetry Collector Docs](https://opentelemetry.io/docs/collector/)
- [Grafana Tempo Docs](https://grafana.com/docs/tempo/latest/)
- [Jaeger Docs](https://www.jaegertracing.io/docs/)
- [MCP Observability Enhancement](https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/269)
