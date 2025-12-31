"""
Troubleshoot Instance Skill - Comprehensive compute instance health analysis.

This skill orchestrates multiple tools to provide:
- Instance state verification
- CPU/memory metric analysis
- Log error detection
- Actionable recommendations
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastmcp import Context
from pydantic import Field, field_validator

from mcp_server_oci.core import (
    BaseSkillInput,
    ResponseFormat,
    SkillMetadata,
    get_client_manager,
    get_logger,
)
from mcp_server_oci.skills.discovery import register_skill_from_metadata
from mcp_server_oci.skills.executor import SkillExecutor, register_skill

logger = get_logger("oci-mcp.skills.troubleshoot")


class TroubleshootInstanceInput(BaseSkillInput):
    """Input parameters for instance troubleshooting skill."""

    instance_id: str = Field(
        ...,
        description="Compute instance OCID to troubleshoot (e.g., 'ocid1.instance.oc1.xxx')",
        min_length=20,
    )
    time_window: str = Field(
        default="1h",
        description="Time window for metrics and logs (e.g., '15m', '1h', '24h')",
    )
    include_logs: bool = Field(
        default=True,
        description="Include log error analysis (requires Log Analytics)",
    )
    check_alarms: bool = Field(
        default=True,
        description="Check for active alarms related to the instance",
    )

    @field_validator("instance_id")
    @classmethod
    def validate_instance_id(cls, v: str) -> str:
        if not v.startswith("ocid1.instance."):
            raise ValueError("Invalid instance OCID format. Expected 'ocid1.instance.oc1...'")
        return v


# Register skill metadata for discovery
SKILL_METADATA = SkillMetadata(
    name="oci_skill_troubleshoot_instance",
    display_name="Troubleshoot Compute Instance",
    domain="compute",
    summary="Comprehensive health check aggregating state, metrics, logs, and alarms",
    full_description="""
Performs a multi-step diagnostic analysis of a compute instance:

1. **State Check**: Verifies instance exists and is running
2. **Metrics Analysis**: Fetches CPU and memory utilization with trend detection
3. **Log Analysis**: Searches for error patterns in Log Analytics (if enabled)
4. **Alarm Check**: Identifies any active alarms for the instance

Returns a synthesized report with health status and actionable recommendations.
    """,
    input_schema=TroubleshootInstanceInput.model_json_schema(),
    tools_used=[
        "oci_observability_get_instance_metrics",
        "oci_observability_execute_log_query",
        "oci_observability_list_alarms",
    ],
    tier=3,
    estimated_duration="5-30s",
)

# Register in both skill registries (executor and discovery)
register_skill(SKILL_METADATA)
register_skill_from_metadata(SKILL_METADATA)


async def troubleshoot_instance(params: TroubleshootInstanceInput, ctx: Context) -> str:
    """
    Perform comprehensive health check on a compute instance.

    Aggregates state, metrics (CPU/memory), recent error logs, and alarms
    to produce an actionable troubleshooting report.

    Args:
        params: TroubleshootInstanceInput with instance_id and options
        ctx: MCP Context for progress reporting

    Returns:
        Troubleshooting report in requested format (markdown or json)

    Example:
        {"instance_id": "ocid1.instance.oc1.xxx", "time_window": "1h"}
    """
    # Initialize executor
    executor = SkillExecutor(
        skill_name="troubleshoot_instance",
        ctx=ctx,
        params=params,
    )

    # Define workflow steps
    executor.add_step("get_instance", "Fetch instance details")
    executor.add_step(
        "get_metrics", "Analyze performance metrics",
        tool_name="get_instance_metrics"
    )
    if params.include_logs:
        executor.add_step(
            "check_logs", "Search for error logs",
            tool_name="execute_log_query"
        )
    if params.check_alarms:
        executor.add_step(
            "check_alarms", "Check active alarms", tool_name="list_alarms"
        )
    executor.add_step("analyze", "Generate recommendations")

    # Storage for findings
    findings: dict[str, Any] = {
        "instance_id": params.instance_id,
        "time_window": params.time_window,
    }
    recommendations: list[str] = []
    overall_success = True

    try:
        client_manager = get_client_manager()

        # Step 1: Get instance details
        instance_result = await executor.run_custom_step(
            "get_instance",
            lambda: _get_instance_details(client_manager, params.instance_id),
        )

        if not instance_result.success:
            return _build_error_response(
                executor, params,
                f"Instance not found or inaccessible: {instance_result.error}"
            )

        instance_data = instance_result.data
        findings["instance"] = {
            "name": instance_data.get("display_name", "Unknown"),
            "state": instance_data.get("lifecycle_state", "UNKNOWN"),
            "shape": instance_data.get("shape", "Unknown"),
            "availability_domain": instance_data.get("availability_domain", "Unknown"),
        }

        # Check if instance is running
        if instance_data.get("lifecycle_state") != "RUNNING":
            state = instance_data.get('lifecycle_state')
            findings["instance"]["warning"] = f"Instance is {state}, not RUNNING"
            recommendations.append(
                f"Instance is {instance_data.get('lifecycle_state')}. "
                "Use oci_compute_start_instance to start it."
            )

        compartment_id = params.compartment_id or instance_data.get("compartment_id")

        # Step 2: Get metrics
        metrics_result = await executor.run_custom_step(
            "get_metrics",
            lambda: _get_instance_metrics(
                client_manager, params.instance_id, compartment_id, params.time_window
            ),
        )

        if metrics_result.success:
            metrics = metrics_result.data
            findings["metrics"] = metrics

            # Analyze CPU
            cpu_avg = metrics.get("cpu", {}).get("average", 0)
            metrics.get("cpu", {}).get("max", 0)

            if cpu_avg > 90:
                findings["metrics"]["cpu_status"] = "CRITICAL"
                recommendations.append(
                    f"CPU is critically high ({cpu_avg:.1f}% avg). "
                    "Consider scaling up the instance shape or investigating high-CPU processes."
                )
            elif cpu_avg > 70:
                findings["metrics"]["cpu_status"] = "WARNING"
                recommendations.append(
                    f"CPU is elevated ({cpu_avg:.1f}% avg). Monitor for sustained high usage."
                )
            else:
                findings["metrics"]["cpu_status"] = "OK"

            # Analyze memory if available
            if "memory" in metrics:
                mem_avg = metrics["memory"].get("average", 0)
                if mem_avg > 90:
                    findings["metrics"]["memory_status"] = "CRITICAL"
                    recommendations.append(
                        f"Memory usage is critical ({mem_avg:.1f}% avg). "
                        "Check for memory leaks or increase instance memory."
                    )
                elif mem_avg > 80:
                    findings["metrics"]["memory_status"] = "WARNING"
                    recommendations.append(
                        f"Memory usage is high ({mem_avg:.1f}% avg). Monitor closely."
                    )
                else:
                    findings["metrics"]["memory_status"] = "OK"
        else:
            findings["metrics"] = {"error": metrics_result.error}
            overall_success = False

        # Step 3: Check logs (if enabled)
        if params.include_logs:
            logs_result = await executor.run_custom_step(
                "check_logs",
                lambda: _check_error_logs(
                    client_manager, params.instance_id, compartment_id, params.time_window
                ),
            )

            if logs_result.success:
                logs_data = logs_result.data
                findings["logs"] = logs_data

                error_count = logs_data.get("error_count", 0)
                if error_count > 100:
                    recommendations.append(
                        f"High error rate detected: {error_count} errors in {params.time_window}. "
                        "Review application logs for patterns."
                    )
                elif error_count > 10:
                    recommendations.append(
                        f"Found {error_count} error logs. Check for recurring issues."
                    )
            else:
                findings["logs"] = {
                    "status": "unavailable",
                    "reason": logs_result.error or "Log Analytics not configured",
                }
                executor.skip_step("check_logs", "Log Analytics unavailable")

        # Step 4: Check alarms (if enabled)
        if params.check_alarms:
            alarms_result = await executor.run_custom_step(
                "check_alarms",
                lambda: _check_instance_alarms(
                    client_manager, params.instance_id, compartment_id
                ),
            )

            if alarms_result.success:
                alarms_data = alarms_result.data
                findings["alarms"] = alarms_data

                firing_alarms = alarms_data.get("firing", [])
                if firing_alarms:
                    for alarm in firing_alarms[:3]:  # Top 3 alarms
                        recommendations.append(
                            f"Active alarm: {alarm.get('name')} (severity: {alarm.get('severity')})"
                        )
            else:
                findings["alarms"] = {"error": alarms_result.error}

        # Step 5: Generate final analysis
        await executor.run_custom_step(
            "analyze",
            lambda: _generate_health_summary(findings),
        )

        # Determine overall health
        health_status = _calculate_health_status(findings)
        findings["health_status"] = health_status

        # Add default recommendation if healthy
        if not recommendations:
            recommendations.append("Instance appears healthy. No immediate action required.")

        # Build result
        summary = _generate_summary(findings, health_status)
        result = executor.build_result(
            success=overall_success,
            summary=summary,
            details=findings,
            recommendations=recommendations,
        )

        # Return in requested format
        if params.response_format == ResponseFormat.JSON:
            return result.model_dump_json(indent=2)
        return result.to_markdown()

    except Exception as e:
        logger.error(f"Troubleshoot skill failed: {e}")
        return _build_error_response(executor, params, str(e))


async def _get_instance_details(client_manager: Any, instance_id: str) -> dict[str, Any]:
    """Fetch instance details from OCI."""
    compute = client_manager.compute
    response = await asyncio.to_thread(
        compute.get_instance,
        instance_id=instance_id,
    )
    instance = response.data
    return {
        "display_name": instance.display_name,
        "lifecycle_state": instance.lifecycle_state,
        "shape": instance.shape,
        "availability_domain": instance.availability_domain,
        "compartment_id": instance.compartment_id,
        "time_created": str(instance.time_created) if instance.time_created else None,
    }


async def _get_instance_metrics(
    client_manager: Any,
    instance_id: str,
    compartment_id: str | None,
    time_window: str,
) -> dict[str, Any]:
    """Fetch CPU and memory metrics for an instance."""
    monitoring = client_manager.monitoring

    # Parse time window
    end_time = datetime.now(UTC)
    if time_window.endswith("m"):
        delta = timedelta(minutes=int(time_window[:-1]))
    elif time_window.endswith("h"):
        delta = timedelta(hours=int(time_window[:-1]))
    elif time_window.endswith("d"):
        delta = timedelta(days=int(time_window[:-1]))
    else:
        delta = timedelta(hours=1)
    start_time = end_time - delta

    # CPU query
    cpu_query = f'CpuUtilization[1m]{{resourceId = "{instance_id}"}}.mean()'
    cpu_response = await asyncio.to_thread(
        monitoring.summarize_metrics_data,
        compartment_id=compartment_id,
        summarize_metrics_data_details={
            "namespace": "oci_computeagent",
            "query": cpu_query,
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
        },
    )

    cpu_data = {"current": 0, "average": 0, "max": 0, "min": 100}
    if cpu_response.data:
        for item in cpu_response.data:
            if item.aggregated_datapoints:
                values = [dp.value for dp in item.aggregated_datapoints if dp.value is not None]
                if values:
                    cpu_data["current"] = round(values[-1], 2)
                    cpu_data["average"] = round(sum(values) / len(values), 2)
                    cpu_data["max"] = round(max(values), 2)
                    cpu_data["min"] = round(min(values), 2)

    # Memory query
    memory_query = f'MemoryUtilization[1m]{{resourceId = "{instance_id}"}}.mean()'
    memory_response = await asyncio.to_thread(
        monitoring.summarize_metrics_data,
        compartment_id=compartment_id,
        summarize_metrics_data_details={
            "namespace": "oci_computeagent",
            "query": memory_query,
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
        },
    )

    memory_data = {"current": 0, "average": 0, "max": 0}
    if memory_response.data:
        for item in memory_response.data:
            if item.aggregated_datapoints:
                values = [dp.value for dp in item.aggregated_datapoints if dp.value is not None]
                if values:
                    memory_data["current"] = round(values[-1], 2)
                    memory_data["average"] = round(sum(values) / len(values), 2)
                    memory_data["max"] = round(max(values), 2)

    return {
        "cpu": cpu_data,
        "memory": memory_data,
        "window": time_window,
    }


async def _check_error_logs(
    client_manager: Any,
    instance_id: str,
    compartment_id: str | None,
    time_window: str,
) -> dict[str, Any]:
    """Search for error logs in Log Analytics."""
    try:
        from oci.log_analytics import LogAnalyticsClient

        config = client_manager._config
        log_analytics = LogAnalyticsClient(config, signer=client_manager._signer)

        # Get namespace
        namespace = os.getenv("LA_NAMESPACE")
        if not namespace:
            namespace_resp = await asyncio.to_thread(
                log_analytics.get_namespace,
                namespace_name=client_manager.tenancy_id,
            )
            namespace = namespace_resp.data.namespace_name

        # Parse time window
        end_time = datetime.now(UTC)
        if time_window.endswith("m"):
            delta = timedelta(minutes=int(time_window[:-1]))
        elif time_window.endswith("h"):
            delta = timedelta(hours=int(time_window[:-1]))
        elif time_window.endswith("d"):
            delta = timedelta(days=int(time_window[:-1]))
        else:
            delta = timedelta(hours=1)
        start_time = end_time - delta

        # Count error logs
        count_query = (
            f"* | where 'Entity' = '{instance_id}' "
            f"and 'Log Level' = 'ERROR' | stats count as ErrorCount"
        )
        count_response = await asyncio.to_thread(
            log_analytics.query,
            namespace_name=namespace,
            query_details={
                "compartmentId": compartment_id or client_manager.tenancy_id,
                "queryString": count_query,
                "subSystem": "LOG",
                "maxTotalCount": 1,
                "timeFilter": {
                    "timeStart": start_time.isoformat(),
                    "timeEnd": end_time.isoformat(),
                },
            },
        )

        error_count = 0
        if count_response.data and count_response.data.results:
            for row in count_response.data.results:
                if hasattr(row, "ErrorCount"):
                    error_count = int(row.ErrorCount)
                    break

        # Get sample errors if count > 0
        samples = []
        if error_count > 0:
            sample_query = (
                f"* | where 'Entity' = '{instance_id}' "
                f"and 'Log Level' = 'ERROR' | head 5"
            )
            sample_response = await asyncio.to_thread(
                log_analytics.query,
                namespace_name=namespace,
                query_details={
                    "compartmentId": compartment_id or client_manager.tenancy_id,
                    "queryString": sample_query,
                    "subSystem": "LOG",
                    "maxTotalCount": 5,
                    "timeFilter": {
                        "timeStart": start_time.isoformat(),
                        "timeEnd": end_time.isoformat(),
                    },
                },
            )
            if sample_response.data and sample_response.data.results:
                for row in sample_response.data.results[:5]:
                    samples.append(str(row))

        return {
            "error_count": error_count,
            "samples": samples,
            "window": time_window,
        }

    except Exception as e:
        raise RuntimeError(f"Log Analytics query failed: {e}") from e


async def _check_instance_alarms(
    client_manager: Any,
    instance_id: str,
    compartment_id: str | None,
) -> dict[str, Any]:
    """Check for active alarms related to the instance."""
    monitoring = client_manager.monitoring

    response = await asyncio.to_thread(
        monitoring.list_alarms,
        compartment_id=compartment_id or client_manager.tenancy_id,
        lifecycle_state="ACTIVE",
        limit=100,
    )

    # Filter alarms that reference this instance
    related_alarms = []
    firing_alarms = []

    for alarm in response.data:
        # Check if alarm query references this instance
        if instance_id in (alarm.query or ""):
            is_firing = (
                alarm.lifecycle_state == "ACTIVE"
                and hasattr(alarm, "is_firing")
                and alarm.is_firing
            )
            alarm_info = {
                "id": alarm.id,
                "name": alarm.display_name,
                "severity": alarm.severity,
                "is_firing": is_firing,
            }
            related_alarms.append(alarm_info)
            if alarm_info.get("is_firing"):
                firing_alarms.append(alarm_info)

    return {
        "total_related": len(related_alarms),
        "firing_count": len(firing_alarms),
        "firing": firing_alarms[:5],  # Top 5 firing alarms
        "all_related": related_alarms[:10],
    }


async def _generate_health_summary(findings: dict[str, Any]) -> str:
    """Generate a text summary of health findings."""
    parts = []

    instance = findings.get("instance", {})
    parts.append(f"Instance {instance.get('name', 'Unknown')} is {instance.get('state', 'UNKNOWN')}")

    if "metrics" in findings and "error" not in findings["metrics"]:
        cpu = findings["metrics"].get("cpu", {})
        parts.append(f"CPU: {cpu.get('average', 0):.1f}% avg")

    if "logs" in findings and findings["logs"].get("error_count", 0) > 0:
        parts.append(f"Errors: {findings['logs']['error_count']}")

    return ". ".join(parts)


def _calculate_health_status(findings: dict[str, Any]) -> str:
    """Calculate overall health status from findings."""
    # Check instance state
    if findings.get("instance", {}).get("state") != "RUNNING":
        return "CRITICAL"

    # Check metrics
    metrics = findings.get("metrics", {})
    cpu_critical = metrics.get("cpu_status") == "CRITICAL"
    mem_critical = metrics.get("memory_status") == "CRITICAL"
    if cpu_critical or mem_critical:
        return "CRITICAL"
    cpu_warn = metrics.get("cpu_status") == "WARNING"
    mem_warn = metrics.get("memory_status") == "WARNING"
    if cpu_warn or mem_warn:
        return "WARNING"

    # Check alarms
    alarms = findings.get("alarms", {})
    if alarms.get("firing_count", 0) > 0:
        return "WARNING"

    # Check logs
    logs = findings.get("logs", {})
    if logs.get("error_count", 0) > 100:
        return "WARNING"

    return "HEALTHY"


def _generate_summary(findings: dict[str, Any], health_status: str) -> str:
    """Generate a human-readable summary."""
    instance_name = findings.get("instance", {}).get("name", "Unknown")
    instance_state = findings.get("instance", {}).get("state", "UNKNOWN")

    cpu_avg = findings.get("metrics", {}).get("cpu", {}).get("average", 0)

    cpu_str = f"{cpu_avg:.1f}%"
    if health_status == "CRITICAL":
        return (
            f"Instance '{instance_name}' requires immediate attention. "
            f"State: {instance_state}, CPU: {cpu_str}"
        )
    elif health_status == "WARNING":
        return (
            f"Instance '{instance_name}' has warnings. "
            f"State: {instance_state}, CPU: {cpu_str}"
        )
    else:
        return (
            f"Instance '{instance_name}' is healthy. "
            f"State: {instance_state}, CPU: {cpu_str}"
        )


def _build_error_response(
    executor: SkillExecutor,
    params: TroubleshootInstanceInput,
    error: str,
) -> str:
    """Build an error response in the requested format."""
    result = executor.build_result(
        success=False,
        summary=f"Troubleshooting failed: {error}",
        details={"error": error},
        recommendations=["Verify the instance OCID is correct and you have read permissions."],
    )

    if params.response_format == ResponseFormat.JSON:
        return result.model_dump_json(indent=2)
    return result.to_markdown()
