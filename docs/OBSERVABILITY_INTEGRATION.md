# MCP-OCI Observability Integration

This document provides comprehensive guidance for integrating MCP-OCI with Oracle Cloud Infrastructure observability services and the local observability stack.

## 🏗️ Architecture Overview

The MCP-OCI observability integration consists of three tiers:

```
┌─────────────────────────────────────────────────────────────────┐
│                    OCI Observability Services                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │  Monitoring │ │ Log Analytics│ │     APM     │ │   Logging   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────┬───────────────────────────────────────┘
                          │ OTLP / OCI SDK
┌─────────────────────────┴───────────────────────────────────────┐
│                  Local Observability Stack                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │  Grafana    │ │ Prometheus  │ │    Tempo    │ │  Pyroscope  ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────┬───────────────────────────────────────┘
                          │ OTLP / Prometheus
┌─────────────────────────┴───────────────────────────────────────┐
│                      MCP Server Layer                          │
│    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│    │   Compute   │ │   Network   │ │    Cost     │           │
│    └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Setup

### 1. Local Observability Stack

```bash
# Start complete observability stack
cd ops
./start-observability.sh

# Verify services
docker-compose ps
curl http://localhost:3000  # Grafana
curl http://localhost:9090  # Prometheus
curl http://localhost:3200  # Tempo
curl http://localhost:4040  # Pyroscope
```

### 2. OCI Integration

Choose your integration approach:

#### Option A: OCI Monitoring (Metrics)
#### Option B: OCI Logging Analytics (Logs & Traces)
#### Option C: OCI APM (Application Performance)
#### Option D: Hybrid (Local + OCI)

## 📊 OCI Monitoring Integration

### Setup OCI Monitoring

```bash
# Environment configuration
export OCI_MONITORING_NAMESPACE=mcp-oci
export OCI_MONITORING_COMPARTMENT_ID=[Link to Secure Variable: OCI_COMPARTMENT_OCID]

# Enable OCI metrics export
export OTEL_EXPORTER_OCI_ENABLED=true
export OTEL_EXPORTER_OCI_ENDPOINT=https://telemetry-ingestion.us-ashburn-1.oraclecloud.com
```

### Custom Metrics Configuration

Create an OCI Monitoring data source in `ops/otel/otel-collector.yaml`:

```yaml
exporters:
  # Existing prometheus exporter
  prometheus:
    endpoint: "0.0.0.0:8889"

  # Add OCI Monitoring exporter
  oci_monitoring:
    endpoint: https://telemetry-ingestion.us-ashburn-1.oraclecloud.com
    namespace: mcp-oci
    compartment_id: ${OCI_MONITORING_COMPARTMENT_ID}
    auth:
      type: oci_config  # or instance_principal/resource_principal
      profile: DEFAULT

service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus, oci_monitoring]  # Dual export
```

### Grafana Dashboard with OCI Data

Add OCI Monitoring as a data source in `ops/grafana/provisioning/datasources/datasources.yaml`:

```yaml
datasources:
  # Existing local datasources
  - name: prometheus
    type: prometheus
    url: http://prometheus:9090

  # Add OCI Monitoring
  - name: oci-monitoring
    type: prometheus
    url: https://telemetry.us-ashburn-1.oraclecloud.com
    jsonData:
      httpMethod: POST
      customQueryParameters: 'compartmentId=${OCI_MONITORING_COMPARTMENT_ID}'
    secureJsonData:
      httpHeaderValue1: 'Bearer ${OCI_AUTH_TOKEN}'
```

### Metrics Available in OCI

The following metrics are automatically exported to OCI Monitoring:

- `mcp_tool_calls_total` - Tool invocation counts by server/tool/outcome
- `mcp_tool_duration_seconds` - Tool execution time histograms
- `http_requests_total` - HTTP request counts by method/endpoint/status
- `http_request_duration_seconds` - HTTP request latency distributions
- `oci_api_calls_total` - OCI SDK API call counts by service/operation
- `oci_api_duration_seconds` - OCI API call latency

## ⚡ Performance and resiliency tunables

Servers enable client reuse and resilient I/O by default. Adjust behavior using environment variables:

General OCI SDK (shared client factory)
- OCI_ENABLE_RETRIES=true|false (default true) — enable OCI SDK retry strategy when supported
- OCI_REQUEST_TIMEOUT=seconds — set both connect/read timeouts
- OCI_REQUEST_TIMEOUT_CONNECT=seconds, OCI_REQUEST_TIMEOUT_READ=seconds — fine‑grained timeouts

Caching (shared disk+memory cache)
- MCP_CACHE_DIR=~/.mcp-oci/cache (default)
- MCP_CACHE_TTL=3600 — default TTL seconds for cache entries

Log Analytics REST (oci-mcp-loganalytics)
- LA_HTTP_POOL=16 — HTTP connection pool size
- LA_HTTP_RETRIES=3 — automatic retries on 429/5xx
- LA_HTTP_BACKOFF=0.2 — per‑request backoff factor
- LA_HTTP_TIMEOUT=60 — per‑request timeout seconds

Networking REST (create_vcn_with_subnets_rest)
- NET_HTTP_POOL=16 — HTTP connection pool size
- NET_HTTP_RETRIES=3 — automatic retries on 429/5xx
- NET_HTTP_BACKOFF=0.2 — per‑request backoff factor

Notes
- SDK clients are reused per (client class, profile, region) to minimize cold‑start/TLS overhead.
- Defaults are production‑safe; increase *_HTTP_POOL for higher concurrency workloads.

## 🔍 OCI Logging Analytics Integration

### Setup Logging Analytics

```bash
# Environment configuration
export OCI_LOG_ANALYTICS_NAMESPACE=mcp-oci
export OCI_LOG_ANALYTICS_LOG_GROUP_ID=[Link to Secure Variable: OCI_LOG_GROUP_OCID]

# Enable log export
export OTEL_EXPORTER_LOGGING_ENABLED=true
```

### OpenTelemetry Configuration

Extend `ops/otel/otel-collector.yaml` for log processing:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  # Add log receiver for application logs
  filelog:
    include: ["/var/log/mcp-servers/*.log"]
    operators:
      - type: json_parser
        timestamp:
          parse_from: attributes.timestamp
          layout: '%Y-%m-%d %H:%M:%S'

processors:
  batch:
  attributes:
    actions:
      - key: oci.compartment_id
        value: ${OCI_LOG_ANALYTICS_COMPARTMENT_ID}
        action: upsert

exporters:
  # Local exports
  prometheus:
    endpoint: "0.0.0.0:8889"
  otlphttp:
    endpoint: "http://tempo:4318"

  # OCI Logging Analytics
  oci_logging:
    endpoint: https://ingestion.logging.us-ashburn-1.oci.oraclecloud.com
    log_group_id: ${OCI_LOG_ANALYTICS_LOG_GROUP_ID}
    auth:
      type: oci_config
      profile: DEFAULT

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, attributes]
      exporters: [otlphttp, oci_logging]  # Export traces to both

    logs:
      receivers: [filelog]
      processors: [batch, attributes]
      exporters: [oci_logging]
```

### Log Structure for OCI

MCP servers emit structured logs compatible with OCI Logging Analytics:

```json
{
  "timestamp": "2024-09-26T10:30:00Z",
  "level": "INFO",
  "service": "mcp-compute",
  "tool": "list_instances",
  "message": "Listed 15 instances",
  "attributes": {
    "mcp.server.name": "oci-mcp-compute",
    "mcp.tool.name": "list_instances",
    "oci.service": "compute",
    "oci.operation": "ListInstances",
    "oci.region": "us-ashburn-1",
    "oci.request_id": "unique-request-id",
    "execution_time_ms": 245
  }
}
```

## 🎯 OCI Application Performance Monitoring (APM)

### Setup OCI APM

```bash
# APM Domain configuration
export OCI_APM_DOMAIN_ID=[Link to Secure Variable: OCI_APM_DOMAIN_OCID]
export OCI_APM_PRIVATE_DATA_KEY="[Link to Secure Variable: OCI_APM_PRIVATE_DATA_KEY]"
export OCI_APM_PUBLIC_DATA_KEY="[Link to Secure Variable: OCI_APM_PUBLIC_DATA_KEY]"

# Enable APM tracing
export OTEL_EXPORTER_APM_ENABLED=true
```

### APM Tracer Configuration

Update `mcp_oci_common/observability.py` for APM integration:

```python
def init_tracing_with_apm(
    service_name: str,
    *,
    apm_domain_id: str | None = None,
    apm_endpoint: str | None = None,
) -> trace.Tracer:
    """Initialize tracing with OCI APM integration"""

    # Dual exporters: local Tempo + OCI APM
    exporters = []

    # Local Tempo (always available)
    tempo_exporter = OTLPSpanExporter(
        endpoint="localhost:4317",
        insecure=True
    )
    exporters.append(BatchSpanProcessor(tempo_exporter))

    # OCI APM (when configured)
    if apm_domain_id:
        apm_exporter = OTLPSpanExporter(
            endpoint=f"https://apm-trace.{os.getenv('OCI_REGION')}.oci.oraclecloud.com/v1/traces",
            headers={
                "Authorization": f"Bearer {os.getenv('OCI_AUTH_TOKEN')}",
                "APM-Domain-Id": apm_domain_id
            }
        )
        exporters.append(BatchSpanProcessor(apm_exporter))

    # Create provider with all exporters
    provider = TracerProvider(resource=_build_resource(service_name))
    for exporter in exporters:
        provider.add_span_processor(exporter)

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
```

### APM Service Map

OCI APM automatically creates service maps from distributed traces. Key span attributes:

- `service.name` - Service identification
- `mcp.server.name` - MCP server name
- `mcp.tool.name` - Tool being executed
- `oci.service` - OCI service being called
- `oci.operation` - Specific OCI operation

## 🔄 Hybrid Integration (Local + OCI)

### Best of Both Worlds

Run local observability for development and OCI services for production monitoring:

```bash
# Development: Local stack only
export ENVIRONMENT=development
export OTEL_EXPORTER_OCI_ENABLED=false

# Production: Dual export to local + OCI
export ENVIRONMENT=production
export OTEL_EXPORTER_OCI_ENABLED=true
export OCI_MONITORING_NAMESPACE=mcp-oci-prod
export OCI_APM_DOMAIN_ID=[Link to Secure Variable: OCI_APM_DOMAIN_OCID]
```

### Environment-Based Configuration

```yaml
# ops/otel/otel-collector.yaml
exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
  otlphttp:
    endpoint: "http://tempo:4318"

  # Conditional OCI exporters
  oci_monitoring:
    endpoint: https://telemetry-ingestion.${OCI_REGION}.oraclecloud.com
    namespace: ${OCI_MONITORING_NAMESPACE}
    # Only enabled in production

service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [batch]
      # Dynamic exporters based on environment
      exporters:
        - prometheus
        - oci_monitoring  # Only if OCI_MONITORING_NAMESPACE set
```

## 📈 Advanced Monitoring Patterns

### Cost-Aware Observability

Monitor OCI API costs alongside application metrics:

```python
# In tool implementations
@tool_span(tracer, "list_instances", mcp_server="oci-mcp-compute")
def list_instances(...):
    with span:
        # Add cost tracking attributes
        span.set_attribute("oci.estimated_cost", 0.001)  # per API call
        span.set_attribute("oci.billable_requests", 1)

        result = compute_client.list_instances(...)

        # Track result size for optimization
        span.set_attribute("oci.response_size", len(result.data))
        span.set_attribute("oci.items_returned", len(result.data))
```

### Resource Correlation

Link OCI resource operations across different MCP servers:

```python
# Generate correlation IDs for multi-server operations
correlation_id = str(uuid.uuid4())

# In compute server
span.set_attribute("correlation_id", correlation_id)
span.set_attribute("resource_type", "instance")
span.set_attribute("resource_ocid", instance_ocid)

# In network server (related operation)
span.set_attribute("correlation_id", correlation_id)
span.set_attribute("resource_type", "vcn")
span.set_attribute("related_instance", instance_ocid)
```

### Alert Definitions

### OCI Monitoring Alerts

Create alerts in OCI Monitoring for critical MCP operations:

```json
{
  "displayName": "MCP Tool Failures",
  "query": "mcp_tool_calls_total[1m]{outcome=\"error\"} > 5",
  "severity": "WARNING",
  "destinations": ["[Link to Secure Variable: OCI_NOTIFICATION_SUBSCRIPTION_OCID]"]
}
```

### Grafana Alerts

Local Grafana alerts for development:

```yaml
# ops/grafana/provisioning/alerting/alerts.yaml
groups:
  - name: mcp_alerts
    rules:
      - alert: MCP_Tool_High_Error_Rate
        expr: rate(mcp_tool_calls_total{outcome="error"}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in MCP tool calls"
```

## 🔒 Security & Compliance

### Observability Data Privacy

- **PII Scrubbing**: Automatically remove sensitive data from traces
- **Retention Policies**: Configure data retention per regulation requirements
- **Access Controls**: Implement RBAC for observability data

```python
# PII scrubbing in spans
def scrub_sensitive_attributes(span: trace.Span):
    # Remove common PII patterns
    for attr_name in ['email', 'ssn', 'credit_card']:
        if span.get_attribute(attr_name):
            span.set_attribute(attr_name, "[REDACTED]")
```

### Compliance Monitoring

Track compliance-related metrics:

```python
compliance_metrics = {
    "data_residency": region,
    "encryption_status": "enabled",
    "access_pattern": "rbac",
    "audit_logged": True
}

for key, value in compliance_metrics.items():
    span.set_attribute(f"compliance.{key}", value)
```

## 🛠️ Troubleshooting

### Common Issues

**OTLP Export Failures**
```bash
# Check collector health
curl http://localhost:8889/metrics | grep otel_

# Verify OCI connectivity
curl -H "Authorization: Bearer $OCI_AUTH_TOKEN" \
  https://telemetry-ingestion.us-ashburn-1.oraclecloud.com/health
```

**Missing Traces in OCI APM**
```bash
# Validate APM configuration
echo $OCI_APM_DOMAIN_ID
echo $OCI_APM_PUBLIC_DATA_KEY

# Check trace sampling
export OTEL_TRACES_SAMPLER=always_on  # Temporary for debugging
```

**High OCI Costs**
```bash
# Reduce sampling rate
export OTEL_TRACES_SAMPLER=traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sampling

# Batch configuration
export OTEL_BSP_MAX_EXPORT_BATCH_SIZE=512
export OTEL_BSP_EXPORT_TIMEOUT=5000
```

### Monitoring the Monitors

Set up health checks for your observability infrastructure:

```bash
#!/bin/bash
# ops/health-check-observability.sh

echo "🔍 Checking Observability Health"

# Local stack
curl -f http://localhost:3000/api/health || echo "❌ Grafana down"
curl -f http://localhost:9090/-/ready || echo "❌ Prometheus down"
curl -f http://localhost:3200/ready || echo "❌ Tempo down"
curl -f http://localhost:4040/ || echo "❌ Pyroscope down"

# OCI endpoints (if configured)
if [[ -n "$OCI_MONITORING_NAMESPACE" ]]; then
    curl -f "https://telemetry-ingestion.${OCI_REGION}.oraclecloud.com/health" || echo "❌ OCI Monitoring unreachable"
fi

echo "✅ Health check complete"
```

This comprehensive observability integration documentation enables users to deploy MCP-OCI with full monitoring capabilities across both local development and OCI production environments.

## 🔧 Pyroscope reliability and auto-disable (noise-free dev)

Some environments intermittently block local HTTP to Pyroscope; to avoid spammy client logs, the stack now probes the backend and auto-disables profiling when unreachable:

- UX app launcher (ops/run-ux-local.sh) checks PYROSCOPE_SERVER_ADDRESS and flips ENABLE_PYROSCOPE=false if the probe fails
- MCP server launcher (scripts/mcp-launchers/start-mcp-server.sh) does the same for each server before starting
- Pyroscope container now uses an explicit config file mount:
  - ops/pyroscope/pyroscope.yaml/config.yaml → /etc/pyroscope.yaml
  - Basic, no-auth config that listens on 0.0.0.0:4040 and stores under /var/lib/pyroscope

Manual override:
- Disable profiling: export ENABLE_PYROSCOPE=false
- Reduce cost: export PYROSCOPE_SAMPLE_RATE=10

## 🌐 HTTP/Streamable HTTP transport for MCP servers

Besides stdio, MCP servers can run with HTTP or streamable HTTP transport for browser/remote clients.

Supported flags via launcher:
- HTTP: ./scripts/mcp-launchers/start-mcp-server.sh observability --http --host 127.0.0.1 --port 8003
- SSE: ./scripts/mcp-launchers/start-mcp-server.sh observability --sse --host 127.0.0.1 --port 8003
- Streamable HTTP: ./scripts/mcp-launchers/start-mcp-server.sh observability --stream --host 127.0.0.1 --port 8003

Environment variables (alternative):
- MCP_TRANSPORT=stdio|http|sse|streamable-http
- MCP_HOST=127.0.0.1
- MCP_PORT=8003

Notes:
- Observability server is transport-aware and will switch based on env/flags.
- Launcher sets defaults: MCP_HOST=127.0.0.1 and MCP_PORT fallback to METRICS_PORT per service.
- Stdio remains the default for local CLI workflows.

## 🐳 Running MCP servers in Docker images

The project Dockerfile supports both the UX (obs-app) and MCP servers.

Run UX app in container (default CMD):
- docker compose -f ops/docker-compose.yml up -d obs-app

Run a specific MCP server in a container:
- Build: docker build -t mcp-oci:latest .
- Run with SERVICE_NAME and transport:
  - StdIO (typical when used by an IDE attaching stdin/stdout): not applicable inside detached containers
  - HTTP:
    - docker run --rm -p 8001:8001 -e SERVICE_NAME=compute -e MCP_TRANSPORT=http -e MCP_HOST=0.0.0.0 -e MCP_PORT=8001 mcp-oci:latest
  - Streamable HTTP:
    - docker run --rm -p 8001:8001 -e SERVICE_NAME=compute -e MCP_TRANSPORT=streamable-http -e MCP_HOST=0.0.0.0 -e MCP_PORT=8001 mcp-oci:latest

Observability envs:
- To wire traces/metrics to the local collector from inside the container:
  - -e OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317 (when on the compose network)
  - -e OTEL_EXPORTER_OTLP_PROTOCOL=grpc
- To enable Pyroscope in-container:
  - -e ENABLE_PYROSCOPE=true -e PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040 -e PYROSCOPE_APP_NAME=oci-mcp-compute
