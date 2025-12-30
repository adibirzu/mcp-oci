---
name: oci-skills
version: 2.0.0
description: High-level workflow skills for OCI operations
parent: oci-mcp
domain: skills
---

# Skills Domain

## Purpose
High-level workflow operations that combine multiple atomic tools to perform complex analysis and troubleshooting tasks. Skills encapsulate expert knowledge and best practices.

## Philosophy

Skills differ from atomic tools in several ways:

1. **Composite Operations**: Skills call multiple tools internally
2. **Expert Logic**: Skills encode operational best practices
3. **Actionable Output**: Skills provide analysis and recommendations
4. **Context Efficiency**: Skills return synthesized results, not raw data

## Available Skills

| Skill | Tier | Description |
|-------|------|-------------|
| `troubleshoot_instance` | 3 | Comprehensive instance troubleshooting |

## Skill: troubleshoot_instance

### Purpose
Automated troubleshooting workflow for compute instances that:
1. Checks instance lifecycle state
2. Retrieves performance metrics (CPU, memory, network)
3. Analyzes health indicators
4. Provides root cause analysis
5. Recommends remediation actions

### Usage
```python
troubleshoot_instance(
    instance_id="ocid1.instance...",
    format="markdown"
)
```

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `instance_id` | string | Yes | Instance OCID to troubleshoot |
| `format` | string | No | Output format (markdown/json) |

### Response Format

#### Markdown Output
```markdown
# Instance Troubleshooting Report

## Instance Information
- **Name:** prod-api-1
- **State:** RUNNING
- **Shape:** VM.Standard.E4.Flex
- **Compartment:** production

## Health Assessment

### ✅ Instance State: HEALTHY
Instance is running normally.

### ⚠️ CPU Utilization: WARNING
- Current: 78.5%
- Average (1h): 72.3%
- **Recommendation:** Consider scaling up OCPU count or optimizing workload.

### ✅ Memory Utilization: HEALTHY
- Current: 45.2%
- Average (1h): 42.1%

### ✅ Network: HEALTHY
- Inbound: 2.3 MB/s
- Outbound: 1.8 MB/s

## Summary
Instance is running but showing elevated CPU usage. Consider:
1. Reviewing running processes
2. Scaling instance shape
3. Implementing auto-scaling
```

#### JSON Output
```json
{
  "instance": {
    "id": "ocid1.instance...",
    "display_name": "prod-api-1",
    "lifecycle_state": "RUNNING",
    "shape": "VM.Standard.E4.Flex"
  },
  "health_checks": [
    {
      "check": "instance_state",
      "status": "healthy",
      "details": "Instance is running normally"
    },
    {
      "check": "cpu_utilization",
      "status": "warning",
      "value": 78.5,
      "threshold": 70,
      "recommendation": "Consider scaling up"
    }
  ],
  "overall_status": "warning",
  "recommendations": [
    "Review running processes",
    "Consider scaling instance shape"
  ]
}
```

### Internal Workflow

The skill internally performs these steps:

```
1. Get instance details (ComputeClient.get_instance)
   ├── Validates instance exists
   └── Gets lifecycle state, shape, compartment

2. Get performance metrics (MonitoringClient.summarize_metrics_data)
   ├── CpuUtilization (last 1 hour)
   ├── MemoryUtilization
   └── NetworkBytesIn/Out

3. Analyze health indicators
   ├── Compare metrics against thresholds
   ├── Classify as healthy/warning/critical
   └── Generate recommendations

4. Format and return report
```

## Future Skills (Planned)

### security_audit
Comprehensive security assessment that checks:
- IAM policies and permissions
- Security lists and NSGs
- Cloud Guard problems
- Audit log anomalies

### cost_analysis
FinOps analysis that provides:
- Monthly spend trends
- Service cost breakdown
- Optimization recommendations
- Budget status

### database_health
Database health check that includes:
- Performance metrics
- Backup status
- Storage utilization
- Connection analysis

## Creating New Skills

Skills should follow this pattern:

```python
@mcp.tool(
    name="skill_name",
    annotations={
        "title": "Human-Readable Title",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def skill_name(params: SkillInput, ctx: Context) -> str:
    """
    Skill description.
    
    This skill performs:
    1. Step one
    2. Step two
    3. Step three
    """
    # Report progress for long operations
    await ctx.report_progress(0.1, "Step 1: Gathering data...")
    
    # Perform analysis
    result = await analyze_something(params)
    
    await ctx.report_progress(0.9, "Formatting results...")
    
    # Format output
    if params.format == "json":
        return json.dumps(result)
    return format_as_markdown(result)
```

## Best Practices

1. **Report Progress**: Use `ctx.report_progress()` for operations >1s
2. **Handle Errors Gracefully**: Return partial results with error context
3. **Provide Recommendations**: Don't just report data, suggest actions
4. **Support Both Formats**: Always implement markdown and JSON output
5. **Document Internal Steps**: Make the workflow transparent in docs
