# Telemetry Configuration Guide

This guide explains how to configure telemetry (tracing, metrics, and logs) for MCP-OCI servers.

## Overview

MCP-OCI supports multiple telemetry backends:
- **OCI APM (Application Performance Monitoring)** - Recommended for production
- **Local OpenTelemetry Collector** - For development and testing
- **Disabled** - For minimal overhead scenarios

## Configuration Priority

The telemetry system uses the following priority order:

1. **OCI APM** (if `OCI_APM_ENDPOINT` and `OCI_APM_PRIVATE_DATA_KEY` are set)
2. **Explicit OTEL Endpoint** (if `OTEL_EXPORTER_OTLP_ENDPOINT` is set)
3. **Local Collector** (default: `localhost:4317` - only if local OTEL not disabled)
4. **Disabled** (if `OTEL_DISABLE_LOCAL=true` and no endpoint configured)

## OCI APM Configuration (Recommended for Production)

OCI APM provides enterprise-grade observability with automatic correlation, dashboards, and alerting.

### Prerequisites

1. **OCI APM Domain**: Create an APM domain in your OCI tenancy
2. **Data Keys**: Generate a private data key for authentication
3. **Endpoint URL**: Get the OTLP endpoint URL from your APM domain

### Setup

**Recommended**: Add to `.env.local` file (automatically loaded):

```bash
# Copy example file
cp .env.local.example .env.local

# Populate these securely (e.g., OCI Vault, local secret manager, or your CI secret store):
OCI_APM_ENDPOINT=[Link to Secure Variable: OCI_APM_ENDPOINT]
OCI_APM_PRIVATE_DATA_KEY=[Link to Secure Variable: OCI_APM_PRIVATE_DATA_KEY]
OTEL_DISABLE_LOCAL=true
```

**Alternative**: Export as environment variables:

```bash
# Set OCI APM endpoint (HTTPS URL)
export OCI_APM_ENDPOINT="https://<apm-domain-id>.apm-<region>.oci.oraclecloud.com/20200101/opentelemetry"

# Set private data key for authentication
export OCI_APM_PRIVATE_DATA_KEY="[Link to Secure Variable: OCI_APM_PRIVATE_DATA_KEY]"

# Optional: Disable local OTEL collector
export OTEL_DISABLE_LOCAL="true"
```

### Endpoint Format

OCI APM endpoints follow this pattern:
```
https://<apm-domain-id>.apm-<region>.oci.oraclecloud.com/20200101/opentelemetry
```

Examples:
- Example: `https://<apm-domain-id>.apm-<region>.oci.oraclecloud.com/20200101/opentelemetry`

### Authentication

OCI APM uses private data keys for authentication. The key is automatically included in the `Authorization` header as:
```
Authorization: dataKey [Link to Secure Variable: OCI_APM_PRIVATE_DATA_KEY]
```

### Verification

After starting a server, check the logs for:
```
[OtelTracing] ✅ Initialized for OCI APM
[OtelTracing] Service: oci-mcp-compute@1.0.0
[OtelTracing] Trace endpoint: https://.../20200101/opentelemetry/private/v1/traces
```

## Local OpenTelemetry Collector (Development)

For local development and testing, you can use a local OpenTelemetry Collector.

### Setup

1. **Start Local Collector**: Use the provided observability stack:
   ```bash
   cd ops
   docker compose up -d
   ```

2. **Configure Endpoint** (optional - defaults to localhost:4317):

   **Recommended**: Add to `.env.local`:
   ```bash
   OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
   OTEL_EXPORTER_OTLP_PROTOCOL=grpc
   ```

   **Alternative**: Export as environment variables:
   ```bash
   export OTEL_EXPORTER_OTLP_ENDPOINT="localhost:4317"
   export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"
   ```

3. **Access Dashboards**:
   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090
   - Tempo: http://localhost:3200

### Disabling Local Collector

To disable the local collector when OCI APM is not configured:

```bash
export OTEL_DISABLE_LOCAL="true"
```

This will disable tracing entirely if no other endpoint is configured.

## Environment Variables Reference

### OCI APM Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OCI_APM_ENDPOINT` | OCI APM OTLP endpoint URL | Yes (for APM) | - |
| `OCI_APM_PRIVATE_DATA_KEY` | Private data key for APM authentication | Yes (for APM) | - |

### OpenTelemetry Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint URL | No | `localhost:4317` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | Protocol (grpc/http/protobuf) | No | `grpc` |
| `OTEL_EXPORTER_OTLP_HEADERS` | Additional headers (comma-separated key=value) | No | - |
| `OTEL_TRACING_ENABLED` | Enable/disable tracing | No | `true` |
| `OTEL_DISABLE_LOCAL` | Disable local collector fallback | No | `false` |
| `OTEL_SERVICE_NAME` | Service name for traces | No | Auto-detected |
| `OTEL_SERVICE_NAMESPACE` | Service namespace | No | `mcp-oci` |
| `DEPLOYMENT_ENVIRONMENT` | Deployment environment tag | No | `local` |

### Service Metadata

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SERVICE_VERSION` | Service version | No | `dev` |
| `SERVICE_TEAM` | Team name | No | - |

## Telemetry Data

### Traces

All MCP tool calls are automatically instrumented with:
- **Service name**: `oci-mcp-<server-name>`
- **Tool name**: The MCP tool being called
- **OCI operation**: Backend OCI API calls
- **Request IDs**: OCI request IDs for correlation
- **Duration**: Execution time
- **Status**: Success/error status

### Metrics

Prometheus metrics are exposed on `/metrics` endpoint (when enabled):
- `mcp_tool_calls_total`: Total tool calls by server, tool, and outcome
- `mcp_tool_duration_seconds`: Tool execution duration histogram
- `oci.mcp.tokens.total`: Token usage (for LLM integrations)

### Logs

Structured logging with correlation IDs:
- Tool execution logs
- Error traces with stack traces
- OCI API call logs

## Troubleshooting

### Traces Not Appearing in OCI APM

1. **Verify Endpoint**: Check that `OCI_APM_ENDPOINT` is correctly set
2. **Verify Authentication**: Ensure `OCI_APM_PRIVATE_DATA_KEY` is valid
3. **Check Network**: Ensure the server can reach the APM endpoint
4. **Check Logs**: Look for initialization errors in server logs

### Local Collector Not Receiving Traces

1. **Verify Collector Running**: `docker ps | grep otel-collector`
2. **Check Port**: Ensure port 4317 is not blocked
3. **Check Protocol**: Verify `OTEL_EXPORTER_OTLP_PROTOCOL` matches collector config

### Disable Telemetry Completely

```bash
export OTEL_TRACING_ENABLED="false"
export OTEL_DISABLE_LOCAL="true"
```

## Best Practices

1. **Production**: Always use OCI APM for production deployments
2. **Development**: Use local collector for faster iteration
3. **Testing**: Disable telemetry in CI/CD to reduce overhead
4. **Security**: Never commit private data keys to version control
5. **Monitoring**: Set up alerts on trace error rates in OCI APM

## Migration from Local to OCI APM

1. Set `OCI_APM_ENDPOINT` and `OCI_APM_PRIVATE_DATA_KEY`
2. Set `OTEL_DISABLE_LOCAL="true"` to disable local collector
3. Restart servers
4. Verify traces appear in OCI APM dashboard
5. Remove local collector configuration

## Additional Resources

- [OCI APM Documentation](https://docs.oracle.com/en-us/iaas/application-performance-monitoring/index.html)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/instrumentation/python/)
- [MCP-OCI Architecture Guide](../ARCHITECTURE.md)
