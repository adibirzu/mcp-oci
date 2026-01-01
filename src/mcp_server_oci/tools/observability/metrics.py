from datetime import UTC, datetime, timedelta
from typing import Any

import oci

from mcp_server_oci.auth import get_client, get_compartment_id, get_oci_config


def _format_metrics_markdown(metrics_data: dict[str, Any], window: str) -> str:
    """Format metrics data into a readable Markdown summary."""
    if "error" in metrics_data:
        return f"Error: {metrics_data['error']}"

    cpu = metrics_data.get("cpu_metrics", {})
    if not cpu:
        return "No metrics available."

    md = f"### CPU Utilization ({window})\n"
    md += f"- **Average:** {cpu.get('average', 0):.2f}%\n"
    md += f"- **Max:** {cpu.get('max', 0):.2f}%\n"
    md += f"- **Min:** {cpu.get('min', 0):.2f}%\n"
    md += f"- **Datapoints:** {cpu.get('datapoints_count', 0)}\n"

    return md

def get_instance_metrics(
    instance_id: str,
    compartment_id: str | None = None,
    window: str = "1h",
    format: str = "markdown"
) -> str | dict:
    """
    Get CPU metrics for a compute instance.

    Args:
        instance_id: The OCID of the instance.
        compartment_id: Optional compartment OCID (defaults to env var).
        window: Time window (e.g., "1h", "24h").
        format: Output format "markdown" or "json".
    """
    comp_id = compartment_id or get_compartment_id()
    if not comp_id:
        # Try to infer compartment from instance details if not provided
        try:
            config = get_oci_config()
            compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
            inst = compute_client.get_instance(instance_id).data
            comp_id = inst.compartment_id
        except Exception:
            msg = "Could not determine compartment ID. Set COMPARTMENT_OCID."
            return {"error": msg}

    config = get_oci_config()
    monitoring_client = get_client(oci.monitoring.MonitoringClient, region=config.get("region"))

    # Calculate time range
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=1) if window == "24h" else end_time - timedelta(hours=1)

    query = f'CpuUtilization[1m]{{resourceId="{instance_id}"}}.mean()'

    try:
        response = monitoring_client.summarize_metrics_data(
            compartment_id=comp_id,
            summarize_metrics_data_details=oci.monitoring.models.SummarizeMetricsDataDetails(
                namespace="oci_computeagent",
                query=query,
                start_time=start_time,
                end_time=end_time
            )
        )

        metrics = []
        if response.data:
            metrics = response.data[0].aggregated_datapoints

        cpu_metrics = {
            'average': sum(dp.value for dp in metrics) / len(metrics) if metrics else 0,
            'max': max(dp.value for dp in metrics) if metrics else 0,
            'min': min(dp.value for dp in metrics) if metrics else 0,
            'datapoints_count': len(metrics)
        }

        result = {'cpu_metrics': cpu_metrics, 'instance_id': instance_id}

        if format == "markdown":
            return _format_metrics_markdown(result, window)
        return result

    except Exception as e:
        return {"error": str(e)}
