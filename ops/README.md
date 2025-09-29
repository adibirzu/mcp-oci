# MCP-OCI Observability Operations

This directory contains the complete observability stack for MCP-OCI servers, providing metrics, tracing, and profiling capabilities.

## 🚀 Quick Start

```bash
# Start the complete observability stack
./restart_observability_stack.sh

# Or start individual components
docker-compose up -d

# Start UX dashboard
./run-ux-local.sh
```

## 📊 Access Points

| Service | URL | Purpose | Credentials |
|---------|-----|---------|-------------|
| **Grafana** | http://localhost:3000 | Dashboards and visualization | admin/admin |
| **Prometheus** | http://localhost:9090 | Metrics collection and querying | - |
| **Tempo** | http://localhost:3200 | Distributed tracing backend | - |
| **Pyroscope** | http://localhost:4040 | Continuous profiling | - |
| **Jaeger** | http://localhost:16686 | Trace exploration and analysis | - |
| **UX Dashboard** | http://localhost:8010 | MCP servers status and control | - |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Servers (8001-8011)                 │
│  compute │ db │ network │ security │ cost │ observability   │
└─────────────────────┬───────────────────────────────────────┘
                      │ Metrics & Traces
┌─────────────────────┴───────────────────────────────────────┐
│                OTLP Collector (4317/8889)                  │
│           Routes metrics and traces to backends            │
└─────────┬─────────────────────────────────────┬─────────────┘
          │ Metrics                             │ Traces
┌─────────▼─────────┐                  ┌────────▼─────────────┐
│   Prometheus      │                  │  Tempo + Jaeger     │
│   (host network)  │                  │  (distributed trace) │
└─────────┬─────────┘                  └────────┬─────────────┘
          │                                     │
          └─────────────┬───────────────────────┘
                        ▼
                ┌───────────────┐
                │    Grafana    │
                │  (localhost)  │
                └───────────────┘
```

## 🔧 Configuration

### Network Setup
- **Prometheus**: Uses host networking mode for localhost target access
- **OTLP Collector**: Exports to both Tempo (HTTP) and Jaeger (gRPC)
- **All Services**: Configured with localhost endpoints for proper connectivity

### Port Mapping
- Prometheus: 9090 (host network)
- Grafana: 3000
- Tempo: 3200, 4318 (OTLP HTTP)
- Pyroscope: 4040, 7946
- Jaeger: 16686 (UI), 14317/14318 (OTLP), 14269 (metrics)
- OTLP Collector: 4317 (gRPC), 8889 (metrics)

## 🧪 Testing & Validation

### End-to-End Test
```bash
# Comprehensive observability pipeline test
cd .. && python test_observability_e2e.py
```

### Generate Test Data
```bash
# Generate metrics (Prometheus format)
python generate_test_data.py --mode metrics

# Generate traces (OpenTelemetry)
python generate_test_data.py --mode traces

# Test all endpoints
python generate_test_data.py --mode test
```

### Health Checks
```bash
# Check container status
docker-compose ps

# Check service health
curl http://localhost:3000/api/health    # Grafana
curl http://localhost:9090/-/ready       # Prometheus
curl http://localhost:3200/api/echo      # Tempo
curl http://localhost:4040/              # Pyroscope
curl http://localhost:14269/             # Jaeger
curl http://localhost:8889/metrics       # OTLP Collector
```

## 🛠️ Operations

### Start/Stop Services
```bash
# Complete restart with cleanup
./restart_observability_stack.sh

# Start services
docker-compose up -d

# Stop services
docker-compose down

# Stop with data cleanup
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f grafana
docker-compose logs -f prometheus
docker-compose logs -f otel-collector
```

### Scaling & Performance
```bash
# Check resource usage
docker stats

# Restart specific service
docker-compose restart grafana

# Update configuration and restart
docker-compose up -d --force-recreate grafana
```

## 🔍 Troubleshooting

### Common Issues

1. **Prometheus targets down**
   - Check MCP servers are running: `scripts/mcp-launchers/start-mcp-server.sh status compute`
   - Verify localhost accessibility from host network

2. **OTLP Collector errors**
   - Check Tempo and Jaeger connectivity
   - Verify port mappings (no conflicts on 4317/4318)

3. **Grafana data source issues**
   - Verify localhost URLs in data source configuration
   - Check service connectivity from Grafana container

4. **Missing traces/metrics**
   - Confirm MCP servers have observability enabled
   - Check OTLP endpoint configuration: `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`

### Debug Commands
```bash
# Check network connectivity
docker-compose exec grafana curl http://localhost:9090/api/v1/targets
docker-compose exec grafana curl http://localhost:3200/api/echo

# Check OTLP collector configuration
docker-compose exec otel-collector cat /etc/otel-collector.yaml

# Restart problematic services
docker-compose restart otel-collector jaeger
```

## 📁 File Structure

```
ops/
├── docker-compose.yml              # Main observability stack
├── restart_observability_stack.sh  # Complete restart script
├── run-ux-local.sh                 # UX dashboard startup
├── generate_test_data.py           # Test data generation
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/            # Grafana data sources (localhost)
│   │   └── dashboards/             # Dashboard configurations
│   └── dashboards/
│       └── mcp-observability.json  # MCP-specific dashboard
├── prometheus/
│   └── prometheus.yml              # Prometheus configuration (localhost targets)
├── tempo/
│   └── tempo.yaml                  # Tempo configuration
├── pyroscope/
│   └── pyroscope.yaml              # Pyroscope configuration
└── otel/
    └── otel-collector.yaml         # OTLP collector configuration
```

## 📈 Available Metrics

### MCP Server Metrics
- `mcp_tool_calls_total` - Total tool invocations by server and tool
- `mcp_tool_duration_seconds` - Tool execution duration histogram
- `http_requests_total` - HTTP request counts
- `http_request_duration_seconds` - HTTP request duration

### Infrastructure Metrics
- `prometheus_*` - Prometheus internal metrics
- `otelcol_*` - OpenTelemetry collector metrics
- `grafana_*` - Grafana internal metrics

### Pre-configured Dashboards
- **MCP Observability**: Comprehensive MCP servers overview with tool metrics, success rates, and duration analysis
- **Service Health**: Infrastructure health monitoring
- **Request Analytics**: HTTP request patterns and performance

---

For detailed configuration and advanced usage, see the main project [README.md](../README.md).