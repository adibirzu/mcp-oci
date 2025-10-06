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
export OCI_MONITORING_COMPARTMENT_ID=ocid1.compartment.oc1..example

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

## 🔍 OCI Logging Analytics Integration

### Setup Logging Analytics

```bash
# Environment configuration
export OCI_LOG_ANALYTICS_NAMESPACE=mcp-oci
export OCI_LOG_ANALYTICS_LOG_GROUP_ID=ocid1.loggroup.oc1..example

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
export OCI_APM_DOMAIN_ID=ocid1.apmdomain.oc1..example
export OCI_APM_PRIVATE_DATA_KEY=your-private-data-key
export OCI_APM_PUBLIC_DATA_KEY=your-public-data-key

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
export OCI_APM_DOMAIN_ID=ocid1.apmdomain.oc1..prod
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
  "destinations": ["ocid1.onssubscription.oc1..example"]
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