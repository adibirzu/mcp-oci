---
name: oci-cost
version: 2.0.0
description: OCI Cost Management and FinOps capabilities
parent: oci-mcp-server
domain: cost
---

# Cost Domain

## Purpose
Comprehensive cost analysis, forecasting, and optimization for Oracle Cloud Infrastructure.

## Available Tools

### Cost Queries
| Tool | Tier | Description |
|------|------|-------------|
| `oci_cost_get_summary` | 2 | Cost summary for time window |
| `oci_cost_by_service` | 2 | Service cost breakdown with top N |
| `oci_cost_by_compartment` | 2 | Compartment hierarchy costs |

### Trend Analysis
| Tool | Tier | Description |
|------|------|-------------|
| `oci_cost_monthly_trend` | 2 | Historical trend with forecast |

### Anomaly Detection
| Tool | Tier | Description |
|------|------|-------------|
| `oci_cost_detect_anomalies` | 3 | Find cost spikes and anomalies |

## Common Patterns

### Monthly Cost Analysis
```python
# 1. Get trend overview
trend = oci_cost_monthly_trend({
    "tenancy_ocid": "ocid1.tenancy...",
    "months_back": 6,
    "include_forecast": True
})

# 2. If spikes detected, drill into anomalies
anomalies = oci_cost_detect_anomalies({
    "tenancy_ocid": "ocid1.tenancy...",
    "time_start": "2024-01-01T00:00:00Z",
    "time_end": "2024-01-31T23:59:59Z",
    "threshold": 2.0
})

# 3. Identify root cause by compartment
breakdown = oci_cost_by_compartment({
    "tenancy_ocid": "ocid1.tenancy...",
    "time_start": "2024-01-01T00:00:00Z",
    "time_end": "2024-01-31T23:59:59Z"
})
```

### Quick Cost Summary
```python
summary = oci_cost_get_summary({
    "tenancy_ocid": "ocid1.tenancy...",
    "time_start": "2024-01-01T00:00:00Z",
    "time_end": "2024-01-31T23:59:59Z",
    "granularity": "DAILY",
    "response_format": "markdown"
})
```

## Response Examples

### Markdown Format
```markdown
# Cost Summary

**Total Cost:** $12,450.67 USD
**Period:** 2024-01-01 to 2024-01-31
**Daily Average:** $401.63

## Cost by Service

| Service | Cost | % of Total |
|---------|------|------------|
| Compute | $5,230.00 | 42.0% |
| Object Storage | $3,100.00 | 24.9% |
| Autonomous DB | $2,450.00 | 19.7% |
```

### JSON Format
```json
{
  "total_cost": 12450.67,
  "currency": "USD",
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-01-31T23:59:59Z",
  "daily_average": 401.63,
  "by_service": [
    {"service": "Compute", "cost": 5230.00, "percentage": 42.0},
    {"service": "Object Storage", "cost": 3100.00, "percentage": 24.9}
  ]
}
```

## Best Practices

1. **Use Markdown for exploration** - Human-readable summaries save tokens
2. **Use JSON for processing** - When you need to calculate or compare data
3. **Start broad, then drill down** - Use summary tools first, then specific tools
4. **Set appropriate time windows** - Longer periods for trends, shorter for anomalies
