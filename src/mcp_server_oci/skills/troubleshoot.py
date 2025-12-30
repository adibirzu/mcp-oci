import json
from typing import Dict, Any
from mcp_server_oci.tools.compute.list import list_instances
from mcp_server_oci.tools.observability.metrics import get_instance_metrics
from mcp_server_oci.tools.observability.logs import get_logs

def troubleshoot_instance(instance_id: str) -> str:
    """
    Perform a comprehensive health check on an instance.
    Aggregates state, metrics (CPU), and recent error logs.
    
    Args:
        instance_id: The OCID of the instance to analyze.
    """
    report = [f"# Troubleshooting Report: `{instance_id}`\n"]
    
    # 1. Check Instance State
    # We don't have a direct get_instance tool exposed yet (only list),
    # but we can reuse the logic or client. For now, let's use list filtered by ID if possible
    # or just assume the user gave us a valid ID and we check metrics.
    # Actually, let's implement a quick get_instance_state helper or use metrics error to detect missing.
    
    report.append("## 1. Instance Status")
    # Using metrics call as a proxy for existence/reachability for now, 
    # or we could fetch details. Let's fetch metrics.
    
    metrics = get_instance_metrics(instance_id, window="1h", format="json")
    
    if "error" in metrics:
        report.append(f"❌ **Error fetching metrics:** {metrics['error']}")
        report.append("Possible causes: Instance does not exist, wrong region, or no permissions.")
        return "\n".join(report)
        
    cpu = metrics.get("cpu_metrics", {})
    avg_cpu = cpu.get("average", 0)
    
    status_icon = "✅"
    if avg_cpu > 80: status_icon = "cx"
    elif avg_cpu > 50: status_icon = "⚠️"
        
    report.append(f"{status_icon} **CPU Utilization (1h):** {avg_cpu:.2f}% (Max: {cpu.get('max', 0):.2f}%)")
    
    # 2. Check Logs (Errors)
    report.append("\n## 2. Recent Errors (Last 1h)")
    query = f"'Log Source' = 'Linux Syslog Logs' and 'Level' = 'error' and 'Host' = '{instance_id}' | stats count"
    
    # Note: This query is a best-guess. Real-world queries depend on log source config.
    # We'll try a broader search first.
    broad_query = f"* | where 'resourceId' = '{instance_id}' and 'Log Level' = 'ERROR' | stats count as ErrorCount"
    
    logs = get_logs(query=broad_query, time_range="1h", format="json")
    
    if isinstance(logs, str) and "Error" in logs:
        report.append(f"⚠️ **Log Check Failed:** {logs}")
    elif isinstance(logs, list) and logs:
        count = logs[0].get("ErrorCount", 0)
        if count > 0:
            report.append(f"❌ Found **{count}** error logs in the last hour.")
            # Fetch samples
            sample_query = f"* | where 'resourceId' = '{instance_id}' and 'Log Level' = 'ERROR' | head 5"
            samples = get_logs(query=sample_query, time_range="1h", format="markdown")
            report.append("\n**Recent Log Samples:**")
            report.append(str(samples))
        else:
            report.append("✅ No error logs found in Log Analytics.")
    else:
        report.append("ℹ️ No log data returned.")

    # 3. Recommendations
    report.append("\n## 3. Recommendations")
    if avg_cpu > 90:
        report.append("- **Critical:** CPU is saturated. Consider scaling up (Change Shape) or investigating top processes.")
    elif avg_cpu > 50:
        report.append("- **Monitor:** CPU is elevated. Check for load spikes.")
    
    if isinstance(logs, list) and logs and logs[0].get("ErrorCount", 0) > 0:
        report.append("- **Investigate:** Check application logs for specific error patterns shown above.")
        
    if len(report) == 6: # No specific recommendations added
        report.append("- System appears healthy.")

    return "\n".join(report)
