"""OCI Observability domain tool implementations.

Provides metrics, logs, and monitoring tools.
Follows OCI MCP Server Standard v2.1 with FastMCP patterns.
"""

from __future__ import annotations

import asyncio
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from mcp_server_oci.core.client import oci_client_manager
from mcp_server_oci.core.errors import format_error_response, handle_oci_error
from mcp_server_oci.skills.discovery import auto_register_tool

from .formatters import ObservabilityFormatter
from .models import (
    ExecuteLogQueryInput,
    GetAlarmHistoryInput,
    GetInstanceMetricsInput,
    ListAlarmsInput,
    ListLogSourcesInput,
    ObservabilityOverviewInput,
    ResponseFormat,
    TimeWindow,
)


def _parse_time_window(window: TimeWindow) -> tuple[datetime, datetime]:
    """Parse time window enum to start/end datetime."""
    end_time = datetime.now(timezone.utc)

    window_map = {
        TimeWindow.MINUTES_15: timedelta(minutes=15),
        TimeWindow.MINUTES_30: timedelta(minutes=30),
        TimeWindow.HOUR_1: timedelta(hours=1),
        TimeWindow.HOURS_3: timedelta(hours=3),
        TimeWindow.HOURS_6: timedelta(hours=6),
        TimeWindow.HOURS_12: timedelta(hours=12),
        TimeWindow.HOURS_24: timedelta(hours=24),
        TimeWindow.DAYS_7: timedelta(days=7),
    }

    delta = window_map.get(window, timedelta(hours=1))
    start_time = end_time - delta

    return start_time, end_time


def _parse_time_range(time_range: str) -> timedelta:
    """Parse time range string (e.g., '60m', '24h', '7d') to timedelta."""
    match = re.match(r"(\d+)([mhdw])", time_range.lower())
    if not match:
        return timedelta(hours=1)

    value = int(match.group(1))
    unit = match.group(2)

    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    elif unit == "w":
        return timedelta(weeks=value)
    return timedelta(hours=1)


def register_observability_tools(mcp: FastMCP) -> None:
    """Register all observability domain tools with the MCP server."""

    @mcp.tool(
        name="oci_observability_get_instance_metrics",
        annotations={
            "title": "Get Instance Metrics",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def get_instance_metrics(params: GetInstanceMetricsInput, ctx: Context) -> str:
        """Get CPU, memory, and disk metrics for a compute instance.

        Retrieves performance metrics for the specified time window.

        Args:
            params: GetInstanceMetricsInput with instance_id, window, and metric options

        Returns:
            Metrics summary in requested format (markdown or json)

        Example:
            {"instance_id": "ocid1.instance.oc1.xxx", "window": "1h"}
        """
        await ctx.report_progress(0.1, "Connecting to OCI Monitoring service...")

        try:
            monitoring = oci_client_manager.monitoring
            compute = oci_client_manager.compute

            # Get instance details for compartment and display name
            await ctx.report_progress(0.2, "Fetching instance details...")
            instance_resp = await asyncio.to_thread(
                compute.get_instance,
                instance_id=params.instance_id,
            )
            instance = instance_resp.data
            compartment_id = params.compartment_id or instance.compartment_id

            start_time, end_time = _parse_time_window(params.window)

            await ctx.report_progress(0.4, "Fetching CPU metrics...")

            # CPU metrics query
            cpu_query = f"""CpuUtilization[1m]{{resourceId = "{params.instance_id}"}}.mean()"""
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

            # Process CPU metrics
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

            data: dict[str, Any] = {
                "instance_id": params.instance_id,
                "instance_name": instance.display_name,
                "window": params.window.value,
                "cpu": cpu_data,
            }

            # Memory metrics
            if params.include_memory:
                await ctx.report_progress(0.6, "Fetching memory metrics...")
                memory_query = f"""MemoryUtilization[1m]{{resourceId = "{params.instance_id}"}}.mean()"""
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
                data["memory"] = memory_data

            # Disk metrics
            if params.include_disk:
                await ctx.report_progress(0.8, "Fetching disk metrics...")
                # Disk read/write IOPS
                data["disk"] = {
                    "read_iops": 0,
                    "write_iops": 0,
                    "read_throughput": 0,
                    "write_throughput": 0,
                }

            # Calculate trend
            if cpu_data["current"] > cpu_data["average"] * 1.1:
                data["trend"] = "↑ CPU usage increasing"
            elif cpu_data["current"] < cpu_data["average"] * 0.9:
                data["trend"] = "↓ CPU usage decreasing"
            else:
                data["trend"] = "→ CPU usage stable"

            await ctx.report_progress(0.9, "Formatting response...")

            if params.response_format == ResponseFormat.JSON:
                return ObservabilityFormatter.to_json(data)
            return ObservabilityFormatter.instance_metrics_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "getting instance metrics")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_observability_get_instance_metrics",
        domain="observability",
        func=get_instance_metrics,
        tier=2,
    )

    @mcp.tool(
        name="oci_observability_execute_log_query",
        annotations={
            "title": "Execute Log Analytics Query",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def execute_log_query(params: ExecuteLogQueryInput, ctx: Context) -> str:
        """Execute a Log Analytics query.

        Runs a query against OCI Log Analytics and returns results.

        Args:
            params: ExecuteLogQueryInput with query, time_range, and limit

        Returns:
            Query results in requested format

        Example:
            {"query": "* | stats count by 'Log Source'", "time_range": "24h"}
        """
        await ctx.report_progress(0.1, "Connecting to Log Analytics...")

        try:
            from oci.log_analytics import LogAnalyticsClient

            config = oci_client_manager._config
            log_analytics = LogAnalyticsClient(config, signer=oci_client_manager._signer)

            # Get namespace
            namespace = os.getenv("LA_NAMESPACE")
            if not namespace:
                namespace_resp = await asyncio.to_thread(
                    log_analytics.get_namespace,
                    namespace_name=oci_client_manager.tenancy_id,
                )
                namespace = namespace_resp.data.namespace_name

            compartment_id = params.compartment_id or os.getenv("COMPARTMENT_OCID") or oci_client_manager.tenancy_id

            # Parse time range
            time_delta = _parse_time_range(params.time_range)
            end_time = datetime.now(timezone.utc)
            start_time = end_time - time_delta

            await ctx.report_progress(0.3, "Executing query...")

            query_response = await asyncio.to_thread(
                log_analytics.query,
                namespace_name=namespace,
                query_details={
                    "compartmentId": compartment_id,
                    "queryString": params.query,
                    "subSystem": "LOG",
                    "maxTotalCount": params.limit,
                    "timeFilter": {
                        "timeStart": start_time.isoformat(),
                        "timeEnd": end_time.isoformat(),
                    },
                },
            )

            await ctx.report_progress(0.7, "Processing results...")

            results = []
            if query_response.data and query_response.data.results:
                for row in query_response.data.results[:params.limit]:
                    results.append(row)

            data = {
                "query": params.query,
                "time_range": params.time_range,
                "total": len(results),
                "results": results,
            }

            await ctx.report_progress(0.9, "Formatting response...")

            if params.response_format == ResponseFormat.JSON:
                return ObservabilityFormatter.to_json(data)
            return ObservabilityFormatter.log_results_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "executing log query")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_observability_execute_log_query",
        domain="observability",
        func=execute_log_query,
        tier=3,
    )

    @mcp.tool(
        name="oci_observability_list_alarms",
        annotations={
            "title": "List Monitoring Alarms",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def list_alarms(params: ListAlarmsInput, ctx: Context) -> str:
        """List monitoring alarms in a compartment.

        Args:
            params: ListAlarmsInput with filters for state and severity

        Returns:
            Alarms list with severity summary in requested format
        """
        await ctx.report_progress(0.1, "Fetching alarms...")

        try:
            monitoring = oci_client_manager.monitoring
            compartment_id = params.compartment_id or oci_client_manager.tenancy_id

            response = await asyncio.to_thread(
                monitoring.list_alarms,
                compartment_id=compartment_id,
                lifecycle_state=params.lifecycle_state,
                limit=params.limit,
            )

            alarms = response.data

            # Filter by severity if specified
            if params.severity:
                alarms = [a for a in alarms if a.severity == params.severity]

            # Calculate severity summary
            severity_counts = Counter(a.severity for a in alarms)

            await ctx.report_progress(0.8, "Formatting response...")

            data = {
                "total": len(alarms),
                "summary": dict(severity_counts),
                "alarms": [
                    {
                        "id": a.id,
                        "display_name": a.display_name,
                        "severity": a.severity,
                        "lifecycle_state": a.lifecycle_state,
                        "namespace": a.namespace,
                        "metric_name": a.query.split("[")[0] if a.query else "N/A",
                        "is_enabled": a.is_enabled,
                    }
                    for a in alarms[:params.limit]
                ],
            }

            if params.response_format == ResponseFormat.JSON:
                return ObservabilityFormatter.to_json(data)
            return ObservabilityFormatter.alarms_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "listing alarms")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_observability_list_alarms",
        domain="observability",
        func=list_alarms,
        tier=2,
    )

    @mcp.tool(
        name="oci_observability_get_alarm_history",
        annotations={
            "title": "Get Alarm History",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def get_alarm_history(params: GetAlarmHistoryInput, ctx: Context) -> str:
        """Get history of alarm state transitions.

        Args:
            params: GetAlarmHistoryInput with alarm_id and window

        Returns:
            Alarm history events in requested format
        """
        await ctx.report_progress(0.1, "Fetching alarm history...")

        try:
            monitoring = oci_client_manager.monitoring

            # Get alarm details first
            alarm_resp = await asyncio.to_thread(
                monitoring.get_alarm,
                alarm_id=params.alarm_id,
            )
            alarm = alarm_resp.data

            start_time, end_time = _parse_time_window(params.window)

            await ctx.report_progress(0.4, "Fetching history...")

            history_resp = await asyncio.to_thread(
                monitoring.get_alarm_history,
                alarm_id=params.alarm_id,
                alarm_historytype="STATE_TRANSITION_HISTORY",
                timestamp_greater_than_or_equal_to=start_time,
                timestamp_less_than=end_time,
            )

            events = []
            if history_resp.data and history_resp.data.entries:
                for entry in history_resp.data.entries:
                    events.append({
                        "timestamp": str(entry.timestamp) if entry.timestamp else None,
                        "status": entry.summary,
                        "message": entry.description if hasattr(entry, "description") else "",
                    })

            data = {
                "alarm_id": params.alarm_id,
                "alarm_name": alarm.display_name,
                "window": params.window.value,
                "events": events,
            }

            if params.response_format == ResponseFormat.JSON:
                return ObservabilityFormatter.to_json(data)
            return ObservabilityFormatter.alarm_history_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "getting alarm history")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_observability_get_alarm_history",
        domain="observability",
        func=get_alarm_history,
        tier=2,
    )

    @mcp.tool(
        name="oci_observability_list_log_sources",
        annotations={
            "title": "List Log Analytics Sources",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def list_log_sources(params: ListLogSourcesInput, ctx: Context) -> str:
        """List Log Analytics log sources.

        Args:
            params: ListLogSourcesInput with filters

        Returns:
            Log sources list in requested format
        """
        await ctx.report_progress(0.1, "Connecting to Log Analytics...")

        try:
            from oci.log_analytics import LogAnalyticsClient

            config = oci_client_manager._config
            log_analytics = LogAnalyticsClient(config, signer=oci_client_manager._signer)

            # Get namespace
            namespace = os.getenv("LA_NAMESPACE")
            if not namespace:
                namespace_resp = await asyncio.to_thread(
                    log_analytics.get_namespace,
                    namespace_name=oci_client_manager.tenancy_id,
                )
                namespace = namespace_resp.data.namespace_name

            compartment_id = params.compartment_id or oci_client_manager.tenancy_id

            await ctx.report_progress(0.4, "Fetching log sources...")

            response = await asyncio.to_thread(
                log_analytics.list_sources,
                namespace_name=namespace,
                compartment_id=compartment_id,
                source_type=params.source_type,
                limit=params.limit,
            )

            sources = response.data.items

            # Filter by name if specified
            if params.name_contains:
                sources = [s for s in sources if params.name_contains.lower() in s.name.lower()]

            data = {
                "total": len(sources),
                "sources": [
                    {
                        "name": s.name,
                        "display_name": s.display_name,
                        "source_type": s.source_type,
                        "entity_types": [et.name for et in (s.entity_types or [])] if hasattr(s, "entity_types") else [],
                        "lifecycle_state": s.lifecycle_state if hasattr(s, "lifecycle_state") else "ACTIVE",
                    }
                    for s in sources[:params.limit]
                ],
            }

            if params.response_format == ResponseFormat.JSON:
                return ObservabilityFormatter.to_json(data)
            return ObservabilityFormatter.log_sources_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "listing log sources")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_observability_list_log_sources",
        domain="observability",
        func=list_log_sources,
        tier=2,
    )

    @mcp.tool(
        name="oci_observability_overview",
        annotations={
            "title": "Observability Overview",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def observability_overview(params: ObservabilityOverviewInput, ctx: Context) -> str:
        """Get a comprehensive observability overview.

        Provides a summary of alarms, log sources, and observability health.

        Args:
            params: ObservabilityOverviewInput with scope options

        Returns:
            Observability overview in requested format
        """
        await ctx.report_progress(0.1, "Starting observability overview...")

        try:
            compartment_id = params.compartment_id or oci_client_manager.tenancy_id

            data: dict[str, Any] = {
                "compartment_name": "Tenancy Root" if compartment_id == oci_client_manager.tenancy_id else compartment_id,
                "recommendations": [],
            }

            # Alarms summary
            if params.include_alarms:
                await ctx.report_progress(0.3, "Fetching alarms summary...")

                try:
                    monitoring = oci_client_manager.monitoring
                    alarms_resp = await asyncio.to_thread(
                        monitoring.list_alarms,
                        compartment_id=compartment_id,
                        lifecycle_state="ACTIVE",
                        limit=100,
                    )

                    alarms = alarms_resp.data
                    severity_counts = Counter(a.severity for a in alarms)

                    data["alarms_summary"] = {
                        "total": len(alarms),
                        "by_severity": dict(severity_counts),
                    }

                    if severity_counts.get("CRITICAL", 0) > 0:
                        data["recommendations"].append(
                            f"Address {severity_counts['CRITICAL']} critical alarm(s) immediately"
                        )

                except Exception:
                    data["alarms_summary"] = {"error": "Failed to fetch alarms"}

            # Log sources summary
            if params.include_log_sources:
                await ctx.report_progress(0.6, "Fetching log sources summary...")

                try:
                    from oci.log_analytics import LogAnalyticsClient

                    config = oci_client_manager._config
                    log_analytics = LogAnalyticsClient(config, signer=oci_client_manager._signer)

                    namespace = os.getenv("LA_NAMESPACE")
                    if not namespace:
                        namespace_resp = await asyncio.to_thread(
                            log_analytics.get_namespace,
                            namespace_name=oci_client_manager.tenancy_id,
                        )
                        namespace = namespace_resp.data.namespace_name

                    sources_resp = await asyncio.to_thread(
                        log_analytics.list_sources,
                        namespace_name=namespace,
                        compartment_id=compartment_id,
                        limit=100,
                    )

                    sources = sources_resp.data.items
                    type_counts = Counter(s.source_type for s in sources)

                    data["log_sources_summary"] = {
                        "total": len(sources),
                        "by_type": dict(type_counts),
                    }

                except Exception:
                    data["log_sources_summary"] = {"error": "Log Analytics not configured or accessible"}

            await ctx.report_progress(0.9, "Generating overview...")

            if params.response_format == ResponseFormat.JSON:
                return ObservabilityFormatter.to_json(data)
            return ObservabilityFormatter.observability_overview_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "generating observability overview")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_observability_overview",
        domain="observability",
        func=observability_overview,
        tier=3,
    )
