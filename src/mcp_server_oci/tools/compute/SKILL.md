---
name: oci-compute
version: 2.0.0
description: OCI Compute instance management capabilities
parent: oci-mcp
domain: compute
---

# Compute Domain

## Purpose
Manage OCI Compute instances including lifecycle operations (start, stop, restart), instance discovery, and performance monitoring.

## Available Tools

### Instance Discovery
| Tool | Tier | Description |
|------|------|-------------|
| `list_instances` | 2 | List compute instances with filtering |

### Lifecycle Management
| Tool | Tier | Description |
|------|------|-------------|
| `start_instance` | 4 | Start a stopped instance |
| `stop_instance` | 4 | Stop a running instance |
| `restart_instance` | 4 | Restart an instance |

### Metrics
| Tool | Tier | Description |
|------|------|-------------|
| `get_instance_metrics` | 2 | Get CPU, memory, network metrics |

## Common Patterns

### List Running Instances
```python
list_instances(
    compartment_id="ocid1.compartment...",
    lifecycle_state="RUNNING",
    limit=20,
    format="markdown"
)
```

### Stop Instance Safely
```python
# 1. First verify instance state
list_instances(
    lifecycle_state="RUNNING",
    format="json"
)

# 2. Then stop (requires ALLOW_MUTATIONS=true)
stop_instance(
    instance_id="ocid1.instance...",
    wait_for_completion=True
)
```

### Monitor Instance Performance
```python
get_instance_metrics(
    instance_id="ocid1.instance...",
    metric_names=["CpuUtilization", "MemoryUtilization"],
    interval="1h"
)
```

## Response Examples

### Markdown Format
```markdown
| Name | State | Shape | IP Address | OCID |
|---|---|---|---|---|
| prod-api-1 | RUNNING | VM.Standard.E4.Flex | 10.0.1.50 | `abc123...` |
| prod-api-2 | RUNNING | VM.Standard.E4.Flex | 10.0.1.51 | `def456...` |
```

### JSON Format
```json
[
  {
    "id": "ocid1.instance...",
    "display_name": "prod-api-1",
    "lifecycle_state": "RUNNING",
    "shape": "VM.Standard.E4.Flex",
    "time_created": "2024-01-15T10:30:00Z"
  }
]
```

## Safety Considerations

1. **Write Operations**: `start_instance`, `stop_instance`, `restart_instance` require `ALLOW_MUTATIONS=true`
2. **Verification First**: Always list/verify before modifying
3. **Production Safeguards**: Consider instance tags before lifecycle changes

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| 404 Not Found | Invalid OCID | Verify instance OCID exists |
| 401 Unauthorized | Bad credentials | Check OCI config file |
| 409 Conflict | Instance busy | Wait and retry |
