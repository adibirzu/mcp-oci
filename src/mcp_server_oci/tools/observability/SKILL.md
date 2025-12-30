---
name: oci-observability
version: 2.0.0
description: OCI Observability and Monitoring capabilities
parent: oci-mcp
domain: observability
---

# Observability Domain

## Purpose
Query logs, metrics, and monitoring data from OCI Logging Analytics and Monitoring services for operational visibility and troubleshooting.

## Available Tools

### Metrics
| Tool | Tier | Description |
|------|------|-------------|
| `get_instance_metrics` | 2 | Get compute instance performance metrics |

### Logging
| Tool | Tier | Description |
|------|------|-------------|
| `get_logs` | 2 | Query OCI Logging Analytics |

## Common Patterns

### Get Instance Metrics
```python
get_instance_metrics(
    instance_id="ocid1.instance...",
    metric_names=["CpuUtilization", "MemoryUtilization"],
    interval="1h",
    format="markdown"
)
```

### Query Logs
```python
get_logs(
    query="* | where severity = 'ERROR'",
    time_start="2024-01-01T00:00:00Z",
    time_end="2024-01-02T00:00:00Z",
    limit=100,
    format="json"
)
```

### Security Event Detection
```python
get_logs(
    query="* | where 'Log Source' = 'OCI Audit Logs' | where eventType contains 'Delete'",
    time_start="2024-01-01T00:00:00Z",
    time_end="2024-01-02T00:00:00Z",
    format="markdown"
)
```

## Response Examples

### Metrics Markdown
```markdown
## Instance Metrics: prod-api-1

**Period:** Last 1 hour
**Instance:** ocid1.instance...

| Metric | Min | Avg | Max |
|--------|-----|-----|-----|
| CPU Utilization | 5.2% | 23.4% | 67.8% |
| Memory Utilization | 45.1% | 52.3% | 61.2% |
| Network In | 1.2 MB | 5.6 MB | 12.3 MB |
```

### Logs JSON
```json
{
  "total": 156,
  "returned": 100,
  "items": [
    {
      "time": "2024-01-01T12:30:45Z",
      "severity": "ERROR",
      "message": "Connection timeout to database",
      "source": "app-server-01"
    }
  ]
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LA_NAMESPACE` | No | Log Analytics namespace override |

## Use Cases

### 1. Performance Troubleshooting
```python
# Get recent metrics for slow instance
get_instance_metrics(
    instance_id="ocid1.instance...",
    metric_names=["CpuUtilization", "DiskReadBytes", "DiskWriteBytes"],
    interval="15m"
)
```

### 2. Error Investigation
```python
# Find recent errors
get_logs(
    query="* | where severity in ('ERROR', 'CRITICAL') | stats count by source",
    time_start="2024-01-01T00:00:00Z",
    time_end="2024-01-01T01:00:00Z"
)
```

### 3. Security Audit
```python
# Check for suspicious activity
get_logs(
    query="'Log Source' = 'OCI Audit Logs' | where eventType contains 'SecurityList'",
    time_start="2024-01-01T00:00:00Z",
    time_end="2024-01-02T00:00:00Z"
)
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Invalid query | Syntax error in Log Analytics query | Check query syntax |
| No data | Empty result set | Expand time range or broaden query |
| 429 Rate Limit | Too many requests | Wait and retry |
