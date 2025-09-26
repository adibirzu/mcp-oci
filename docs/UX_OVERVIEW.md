# MCP-OCI UX Overview

The MCP-OCI UX application provides a web-based interface for monitoring and interacting with your MCP server infrastructure. It integrates with the complete observability stack to provide real-time visibility into server operations, tool usage, and system performance.

## 🚀 Quick Start

### 1. Start the UX Application

```bash
# From the ops directory
cd ops
./run-ux-local.sh

# Or manually
cd ux
python app.py
```

The UX application will be available at: http://localhost:8010

### 2. Access Observability Dashboards

- **MCP Overview**: http://localhost:8010
- **Grafana Dashboards**: http://localhost:8010/dashboards
- **Health Check**: http://localhost:8010/health

## 📊 Features

### Server Overview

The main dashboard provides:

- **Real-time Server Status**: Live status of all MCP servers
- **Tool Catalog**: Complete listing of available tools with schemas
- **Relations Diagram**: Visual representation of server architecture using Mermaid diagrams
- **Discovery Registry**: Name→OCID mappings and resource discovery status

### Observability Integration

- **Metrics Dashboard**: Prometheus metrics visualization via Grafana
- **Distributed Tracing**: Request tracing through Tempo integration
- **Continuous Profiling**: Performance profiling via Pyroscope
- **Log Aggregation**: Centralized logging for all MCP operations

### Interactive Features

- **Tool Documentation**: Expandable tool details with input schemas
- **Environment Configuration**: View server environment settings
- **Health Monitoring**: Real-time health status for all services

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        UX Frontend                              │
│                    (FastAPI + Jinja2)                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                  MCP Server Discovery                          │
│    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│    │   Compute   │ │   Network   │ │    Cost     │           │
│    └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                 Observability Stack                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │  Grafana    │ │ Prometheus  │ │    Tempo    │ │  Pyroscope  ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Configuration

### Environment Variables

```bash
# UX Application
PYROSCOPE_APP_NAME=mcp-ux                    # Pyroscope application name
PYROSCOPE_SERVER_ADDRESS=http://localhost:4040  # Pyroscope server
PYROSCOPE_SAMPLE_RATE=100                    # Profiling sample rate (Hz)
ENABLE_PYROSCOPE=true                        # Enable continuous profiling

# Observability Integration
OTEL_SERVICE_NAME=mcp-ux                     # OpenTelemetry service name
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317  # OTLP collector endpoint
GRAFANA_URL=http://localhost:3000           # Grafana dashboard URL
PROMETHEUS_URL=http://localhost:9090         # Prometheus metrics URL
TEMPO_URL=http://localhost:3200             # Tempo tracing URL
```

### Static Assets

```bash
ux/
├── static/
│   └── styles.css          # Custom CSS styling
├── templates/
│   ├── index.html          # Main dashboard template
│   └── dashboard.html      # Grafana dashboard links
└── app.py                  # FastAPI application
```

## 📈 Monitoring & Metrics

### Built-in Metrics

The UX application exposes the following metrics at `/metrics`:

- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request duration histogram
- Custom application metrics for server discovery and tool usage

### Distributed Tracing

- All HTTP requests are traced with OpenTelemetry
- Traces include server discovery operations and tool schema generation
- Traces are exported to Tempo via OTLP collector

### Continuous Profiling

- CPU and memory profiling enabled by default
- Profiles exported to Pyroscope for performance analysis
- Configurable sample rates for production environments

## 🗂️ Server Discovery

The UX dynamically discovers and catalogs MCP servers by:

1. **Reading Configuration**: Loads server definitions from `mcp.json`
2. **Module Introspection**: Dynamically imports server modules
3. **Schema Generation**: Extracts tool schemas via reflection
4. **Registry Integration**: Connects with resource discovery registry

### Supported Server Types

| Server | Module | Tools Discovered |
|--------|--------|------------------|
| Compute | `mcp_servers.compute.server` | Instance management, scaling |
| Database | `mcp_servers.db.server` | ADB operations, backups |
| Network | `mcp_servers.network.server` | VCN, subnet, security management |
| Security | `mcp_servers.security.server` | Vulnerability scanning, compliance |
| Cost | `mcp_servers.cost.server` | Cost analysis, forecasting |
| Block Storage | `mcp_servers.blockstorage.server` | Volume management, backups |
| Observability | `mcp_servers.observability.server` | Monitoring, alerting |
| Inventory | `mcp_servers.inventory.server` | Resource discovery, tagging |
| Load Balancer | `mcp_servers.loadbalancer.server` | LB configuration, health checks |

## 🔍 Troubleshooting

### Common Issues

**UX Application Won't Start**
```bash
# Check Python dependencies
pip install -r requirements.txt

# Verify FastAPI installation
python -c "import fastapi; print('FastAPI OK')"
```

**Server Discovery Failing**
```bash
# Check MCP server modules
python -c "import mcp_servers.compute.server; print('Compute OK')"

# Verify mcp.json configuration
cat mcp.json | jq .
```

**Observability Stack Not Connected**
```bash
# Verify observability services are running
docker-compose ps

# Test OTLP endpoint connectivity
curl -v http://localhost:4317/v1/traces
```

### Log Analysis

```bash
# UX application logs (if running with systemd/supervisor)
journalctl -u mcp-ux -f

# Docker container logs
docker-compose logs ux

# Manual debugging
python ux/app.py
```

## 🎯 Production Deployment

### Docker Deployment

```yaml
# docker-compose.yml addition
services:
  ux:
    build: ./ux
    ports:
      - "8010:8000"
    environment:
      - GRAFANA_URL=https://grafana.yourdomain.com
      - PROMETHEUS_URL=https://prometheus.yourdomain.com
    depends_on:
      - grafana
      - prometheus
      - tempo
```

### Security Considerations

- **Authentication**: Add authentication middleware for production
- **HTTPS**: Use reverse proxy (nginx/traefik) for SSL termination
- **CORS**: Configure CORS policies for cross-origin requests
- **Rate Limiting**: Implement rate limiting for API endpoints

### Performance Tuning

```bash
# Production configuration
export PYROSCOPE_SAMPLE_RATE=10     # Reduce profiling overhead
export ENABLE_PYROSCOPE=false       # Disable in high-traffic scenarios
export WORKERS=4                    # Increase uvicorn workers

# Start with optimized settings
uvicorn ux.app:app --workers 4 --host 0.0.0.0 --port 8010
```

## 📚 Development

### Adding Custom Views

```python
# ux/app.py
@app.get("/custom-view")
async def custom_view(request: Request):
    # Custom logic here
    payload = {"custom_data": "value"}
    return templates.TemplateResponse(request, "custom.html", payload)
```

### Extending Server Discovery

```python
# Add custom server type to module_map
module_map = {
    'oci-mcp-custom': 'mcp_servers.custom.server',
    # ... existing mappings
}
```

### Custom Metrics

```python
# Add custom metrics
from prometheus_client import Counter, Gauge

custom_metric = Counter('mcp_custom_operations_total', 'Custom operations')

@app.get("/custom-endpoint")
async def custom_endpoint():
    custom_metric.inc()
    return {"status": "ok"}
```

This comprehensive UX overview provides users with everything they need to understand, deploy, and extend the MCP-OCI web interface.