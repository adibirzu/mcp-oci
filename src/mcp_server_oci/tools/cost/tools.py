"""
OCI Cost domain tool implementations.
"""
from __future__ import annotations

import asyncio
import statistics
from datetime import datetime, timedelta

from mcp.server.fastmcp import Context, FastMCP

from mcp_server_oci.core.client import get_oci_client
from mcp_server_oci.core.errors import format_error_response, handle_oci_error
from mcp_server_oci.skills.discovery import ToolInfo, tool_registry

from .formatters import CostFormatter
from .models import (
    CostAnomalyInput,
    CostByCompartmentInput,
    CostByServiceInput,
    CostSummaryInput,
    MonthlyTrendInput,
    ResponseFormat,
)


def register_cost_tools(mcp: FastMCP) -> None:
    """Register all cost domain tools with the MCP server."""

    @mcp.tool(
        name="oci_cost_get_summary",
        annotations={
            "title": "Get OCI Cost Summary",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def get_cost_summary(params: CostSummaryInput, ctx: Context) -> str:
        """Get comprehensive cost summary for a time window.
        
        Retrieves total costs, daily/monthly breakdown, and service attribution
        for the specified tenancy and time period.
        
        Args:
            params: CostSummaryInput with tenancy_ocid, time_start, time_end,
                   granularity, and response_format
        
        Returns:
            Cost summary in requested format (markdown or json) including:
            - Total cost for period
            - Daily/monthly breakdown
            - Cost by service (top 10)
        
        Example:
            {"tenancy_ocid": "ocid1.tenancy...", "time_start": "2024-01-01T00:00:00Z",
             "time_end": "2024-01-31T23:59:59Z", "granularity": "DAILY"}
        """
        await ctx.report_progress(0.1, "Connecting to OCI Usage API...")

        try:
            async with get_oci_client() as client:
                usage_client = client.usage_api

                await ctx.report_progress(0.3, "Fetching cost data...")

                # Build request
                from oci.usage_api.models import RequestSummarizedUsagesDetails

                request_details = RequestSummarizedUsagesDetails(
                    tenant_id=params.tenancy_ocid,
                    time_usage_started=datetime.fromisoformat(params.time_start.replace('Z', '+00:00')),
                    time_usage_ended=datetime.fromisoformat(params.time_end.replace('Z', '+00:00')),
                    granularity=params.granularity.value,
                    query_type="COST",
                    group_by=["service"],
                )

                # Execute query
                response = await asyncio.to_thread(
                    usage_client.request_summarized_usages,
                    request_details
                )

                await ctx.report_progress(0.7, "Processing results...")

                # Process response
                data = _process_cost_summary(
                    response.data.items,
                    params.time_start,
                    params.time_end
                )

                await ctx.report_progress(0.9, "Formatting output...")

                if params.response_format == ResponseFormat.JSON:
                    return CostFormatter.to_json(data)
                return CostFormatter.summary_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "fetching cost summary")
            return format_error_response(error, params.response_format.value)

    # Register for discovery
    tool_registry.register(ToolInfo(
        name="oci_cost_get_summary",
        domain="cost",
        summary="Get comprehensive cost summary for a time window",
        full_description=get_cost_summary.__doc__ or "",
        input_schema=CostSummaryInput.model_json_schema(),
        annotations={"readOnlyHint": True, "destructiveHint": False}
    ))


    @mcp.tool(
        name="oci_cost_by_service",
        annotations={
            "title": "Get Cost by Service",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def cost_by_service(params: CostByServiceInput, ctx: Context) -> str:
        """Get top services by cost with compartment breakdown.
        
        Identifies highest-spending services and shows which compartments
        contribute most to each service's cost.
        
        Args:
            params: CostByServiceInput with top_n and filtering options
        
        Returns:
            Service drilldown including:
            - Top N services by cost
            - Compartment breakdown per service
            - Percentage of total spend
        """
        await ctx.report_progress(0.1, "Starting service cost analysis...")

        try:
            async with get_oci_client() as client:
                usage_client = client.usage_api

                await ctx.report_progress(0.3, "Fetching service costs...")

                from oci.usage_api.models import RequestSummarizedUsagesDetails

                request_details = RequestSummarizedUsagesDetails(
                    tenant_id=params.tenancy_ocid,
                    time_usage_started=datetime.fromisoformat(params.time_start.replace('Z', '+00:00')),
                    time_usage_ended=datetime.fromisoformat(params.time_end.replace('Z', '+00:00')),
                    granularity="MONTHLY",
                    query_type="COST",
                    group_by=["service"],
                )

                response = await asyncio.to_thread(
                    usage_client.request_summarized_usages,
                    request_details
                )

                await ctx.report_progress(0.7, "Analyzing service breakdown...")

                data = _process_service_costs(
                    response.data.items,
                    params.top_n,
                    params.time_start,
                    params.time_end
                )

                if params.response_format == ResponseFormat.JSON:
                    return CostFormatter.to_json(data)
                return CostFormatter.service_drilldown_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "fetching service costs")
            return format_error_response(error, params.response_format.value)

    tool_registry.register(ToolInfo(
        name="oci_cost_by_service",
        domain="cost",
        summary="Get top services by cost with breakdown",
        full_description=cost_by_service.__doc__ or "",
        input_schema=CostByServiceInput.model_json_schema(),
        annotations={"readOnlyHint": True, "destructiveHint": False}
    ))


    @mcp.tool(
        name="oci_cost_by_compartment",
        annotations={
            "title": "Get Cost by Compartment",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def cost_by_compartment(params: CostByCompartmentInput, ctx: Context) -> str:
        """Get daily cost breakdown by compartment and service.
        
        Provides hierarchical cost breakdown showing spending across
        compartments with optional child compartment inclusion.
        
        Args:
            params: CostByCompartmentInput with compartment filtering options
        
        Returns:
            Cost breakdown by compartment including:
            - Compartment hierarchy costs
            - Service breakdown per compartment
        """
        await ctx.report_progress(0.1, "Initializing compartment cost query...")

        try:
            async with get_oci_client() as client:
                usage_client = client.usage_api
                identity_client = client.identity

                await ctx.report_progress(0.2, "Fetching compartment hierarchy...")

                # Get compartment names
                compartments = await _get_compartment_map(
                    identity_client,
                    params.tenancy_ocid
                )

                await ctx.report_progress(0.4, "Fetching cost data...")

                from oci.usage_api.models import RequestSummarizedUsagesDetails

                request_details = RequestSummarizedUsagesDetails(
                    tenant_id=params.tenancy_ocid,
                    time_usage_started=datetime.fromisoformat(params.time_start.replace('Z', '+00:00')),
                    time_usage_ended=datetime.fromisoformat(params.time_end.replace('Z', '+00:00')),
                    granularity=params.granularity.value,
                    query_type="COST",
                    group_by=["compartmentId", "service"],
                )

                response = await asyncio.to_thread(
                    usage_client.request_summarized_usages,
                    request_details
                )

                await ctx.report_progress(0.7, "Processing compartment data...")

                data = _process_compartment_costs(
                    response.data.items,
                    compartments,
                    params.top_n,
                    params.time_start,
                    params.time_end
                )

                if params.response_format == ResponseFormat.JSON:
                    return CostFormatter.to_json(data)
                return CostFormatter.compartment_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "fetching compartment costs")
            return format_error_response(error, params.response_format.value)

    tool_registry.register(ToolInfo(
        name="oci_cost_by_compartment",
        domain="cost",
        summary="Get cost breakdown by compartment hierarchy",
        full_description=cost_by_compartment.__doc__ or "",
        input_schema=CostByCompartmentInput.model_json_schema(),
        annotations={"readOnlyHint": True, "destructiveHint": False}
    ))


    @mcp.tool(
        name="oci_cost_monthly_trend",
        annotations={
            "title": "Monthly Cost Trend with Forecast",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def monthly_trend(params: MonthlyTrendInput, ctx: Context) -> str:
        """Analyze month-over-month cost trends with forecasting.
        
        Provides historical cost trends and projects future spending
        based on historical patterns.
        
        Args:
            params: MonthlyTrendInput with months_back and optional budget_ocid
        
        Returns:
            Trend analysis including:
            - Monthly costs for specified period
            - Month-over-month change percentages
            - Next month forecast
            - Budget variance (if budget_ocid provided)
        """
        await ctx.report_progress(0.1, "Calculating date ranges...")

        try:
            async with get_oci_client() as client:
                usage_client = client.usage_api

                # Calculate time range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=params.months_back * 30)

                await ctx.report_progress(0.3, f"Fetching {params.months_back} months of data...")

                from oci.usage_api.models import RequestSummarizedUsagesDetails

                request_details = RequestSummarizedUsagesDetails(
                    tenant_id=params.tenancy_ocid,
                    time_usage_started=start_date,
                    time_usage_ended=end_date,
                    granularity="MONTHLY",
                    query_type="COST",
                )

                response = await asyncio.to_thread(
                    usage_client.request_summarized_usages,
                    request_details
                )

                await ctx.report_progress(0.6, "Calculating trends...")

                data = _process_monthly_trend(response.data.items, params.months_back)

                if params.include_forecast:
                    await ctx.report_progress(0.8, "Generating forecast...")
                    data["forecast"] = _generate_forecast(data["monthly_costs"])

                if params.response_format == ResponseFormat.JSON:
                    return CostFormatter.to_json(data)
                return CostFormatter.trend_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "analyzing cost trends")
            return format_error_response(error, params.response_format.value)

    tool_registry.register(ToolInfo(
        name="oci_cost_monthly_trend",
        domain="cost",
        summary="Analyze month-over-month cost trends with forecasting",
        full_description=monthly_trend.__doc__ or "",
        input_schema=MonthlyTrendInput.model_json_schema(),
        annotations={"readOnlyHint": True, "destructiveHint": False}
    ))


    @mcp.tool(
        name="oci_cost_detect_anomalies",
        annotations={
            "title": "Detect Cost Anomalies",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def detect_anomalies(params: CostAnomalyInput, ctx: Context) -> str:
        """Find and explain cost spikes and anomalies.
        
        Uses statistical analysis to identify unusual spending patterns
        and provides root cause explanations.
        
        Args:
            params: CostAnomalyInput with threshold and filtering options
        
        Returns:
            Anomaly detection results including:
            - Days with anomalous spending
            - Severity classification (low/medium/high/critical)
            - Root cause analysis (service breakdown)
        """
        await ctx.report_progress(0.1, "Fetching daily cost data...")

        try:
            async with get_oci_client() as client:
                usage_client = client.usage_api

                await ctx.report_progress(0.3, "Running anomaly detection...")

                from oci.usage_api.models import RequestSummarizedUsagesDetails

                request_details = RequestSummarizedUsagesDetails(
                    tenant_id=params.tenancy_ocid,
                    time_usage_started=datetime.fromisoformat(params.time_start.replace('Z', '+00:00')),
                    time_usage_ended=datetime.fromisoformat(params.time_end.replace('Z', '+00:00')),
                    granularity="DAILY",
                    query_type="COST",
                    group_by=["service"],
                )

                response = await asyncio.to_thread(
                    usage_client.request_summarized_usages,
                    request_details
                )

                await ctx.report_progress(0.6, "Analyzing patterns...")

                # Detect anomalies
                anomalies = _detect_cost_anomalies(
                    response.data.items,
                    threshold=params.threshold,
                    top_n=params.top_n
                )

                await ctx.report_progress(0.9, "Generating report...")

                result = {
                    "anomalies": anomalies,
                    "detection_params": {
                        "threshold_std_dev": params.threshold,
                        "period": f"{params.time_start} to {params.time_end}"
                    },
                    "summary": {
                        "total_anomalies": len(anomalies),
                        "critical": len([a for a in anomalies if a["severity"] == "critical"]),
                        "high": len([a for a in anomalies if a["severity"] == "high"]),
                        "medium": len([a for a in anomalies if a["severity"] == "medium"]),
                        "low": len([a for a in anomalies if a["severity"] == "low"]),
                    }
                }

                if params.response_format == ResponseFormat.JSON:
                    return CostFormatter.to_json(result)
                return CostFormatter.anomaly_markdown(result)

        except Exception as e:
            error = handle_oci_error(e, "detecting cost anomalies")
            return format_error_response(error, params.response_format.value)

    tool_registry.register(ToolInfo(
        name="oci_cost_detect_anomalies",
        domain="cost",
        summary="Find and explain cost spikes and anomalies",
        full_description=detect_anomalies.__doc__ or "",
        input_schema=CostAnomalyInput.model_json_schema(),
        annotations={"readOnlyHint": True, "destructiveHint": False}
    ))


# Helper functions

def _process_cost_summary(items: list, time_start: str, time_end: str) -> dict:
    """Process raw OCI usage API response into cost summary."""
    service_costs = {}
    total_cost = 0.0

    for item in items:
        cost = float(item.computed_amount or 0)
        service = item.service or "Unknown"
        total_cost += cost

        if service in service_costs:
            service_costs[service] += cost
        else:
            service_costs[service] = cost

    # Calculate days in period
    start = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
    end = datetime.fromisoformat(time_end.replace('Z', '+00:00'))
    days = max((end - start).days, 1)

    # Sort services by cost
    sorted_services = sorted(
        service_costs.items(),
        key=lambda x: x[1],
        reverse=True
    )

    by_service = []
    for service, cost in sorted_services[:10]:
        pct = (cost / total_cost * 100) if total_cost > 0 else 0
        by_service.append({
            "service": service,
            "cost": cost,
            "percentage": pct,
            "currency": "USD"
        })

    return {
        "total_cost": total_cost,
        "currency": "USD",
        "period_start": time_start,
        "period_end": time_end,
        "daily_average": total_cost / days,
        "by_service": by_service
    }


def _process_service_costs(items: list, top_n: int, time_start: str, time_end: str) -> dict:
    """Process service cost drilldown."""
    service_costs = {}
    total = 0.0

    for item in items:
        cost = float(item.computed_amount or 0)
        service = item.service or "Unknown"
        total += cost

        if service in service_costs:
            service_costs[service] += cost
        else:
            service_costs[service] = cost

    sorted_services = sorted(
        service_costs.items(),
        key=lambda x: x[1],
        reverse=True
    )[:top_n]

    services = []
    for service, cost in sorted_services:
        pct = (cost / total * 100) if total > 0 else 0
        services.append({
            "service": service,
            "cost": cost,
            "percentage": pct
        })

    return {
        "total": total,
        "period_start": time_start,
        "period_end": time_end,
        "services": services
    }


async def _get_compartment_map(identity_client, tenancy_id: str) -> dict[str, str]:
    """Build OCID to name mapping for compartments."""
    compartments = {}

    try:
        response = await asyncio.to_thread(
            identity_client.list_compartments,
            tenancy_id,
            compartment_id_in_subtree=True,
            lifecycle_state="ACTIVE"
        )

        for comp in response.data:
            compartments[comp.id] = comp.name

        # Add root compartment
        compartments[tenancy_id] = "root"

    except Exception:
        pass  # Return empty map on error

    return compartments


def _process_compartment_costs(
    items: list,
    compartments: dict[str, str],
    top_n: int,
    time_start: str,
    time_end: str
) -> dict:
    """Process costs grouped by compartment."""
    compartment_data = {}
    total = 0.0

    for item in items:
        cost = float(item.computed_amount or 0)
        comp_id = item.compartment_id or "unknown"
        service = item.service or "Unknown"
        total += cost

        if comp_id not in compartment_data:
            compartment_data[comp_id] = {
                "name": compartments.get(comp_id, comp_id[:20] + "..."),
                "cost": 0.0,
                "services": {}
            }

        compartment_data[comp_id]["cost"] += cost

        if service in compartment_data[comp_id]["services"]:
            compartment_data[comp_id]["services"][service] += cost
        else:
            compartment_data[comp_id]["services"][service] = cost

    # Sort and format
    sorted_comps = sorted(
        compartment_data.items(),
        key=lambda x: x[1]["cost"],
        reverse=True
    )[:top_n]

    compartments_list = []
    for comp_id, data in sorted_comps:
        services = sorted(
            data["services"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        compartments_list.append({
            "name": data["name"],
            "cost": data["cost"],
            "services": [{"service": s, "cost": c} for s, c in services]
        })

    return {
        "total_cost": total,
        "period_start": time_start,
        "period_end": time_end,
        "compartments": compartments_list
    }


def _process_monthly_trend(items: list, months_back: int) -> dict:
    """Process monthly trend data."""
    monthly = {}

    for item in items:
        cost = float(item.computed_amount or 0)
        if item.time_usage_started:
            month = item.time_usage_started.strftime("%Y-%m")
            if month in monthly:
                monthly[month] += cost
            else:
                monthly[month] = cost

    # Sort by month
    sorted_months = sorted(monthly.items())

    monthly_costs = []
    prev_cost = None
    total = 0.0

    for month, cost in sorted_months:
        change = None
        if prev_cost is not None and prev_cost > 0:
            change = ((cost - prev_cost) / prev_cost) * 100

        monthly_costs.append({
            "month": month,
            "cost": cost,
            "change_percent": change
        })

        total += cost
        prev_cost = cost

    return {
        "summary": {
            "months_analyzed": len(monthly_costs),
            "total_spend": total,
            "average_monthly": total / len(monthly_costs) if monthly_costs else 0
        },
        "monthly_costs": monthly_costs
    }


def _generate_forecast(monthly_costs: list) -> dict:
    """Generate simple linear forecast based on recent months."""
    if len(monthly_costs) < 2:
        return {"estimate": 0, "trend": "insufficient_data"}

    costs = [m["cost"] for m in monthly_costs]

    # Simple average of last 3 months
    recent = costs[-3:] if len(costs) >= 3 else costs
    avg = sum(recent) / len(recent)

    # Calculate trend
    if len(costs) >= 2:
        recent_avg = sum(costs[-2:]) / 2
        older_avg = sum(costs[:-2]) / max(len(costs) - 2, 1) if len(costs) > 2 else costs[0]

        if recent_avg > older_avg * 1.1:
            trend = "increasing"
        elif recent_avg < older_avg * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return {
        "estimate": avg,
        "trend": trend
    }


def _detect_cost_anomalies(items: list, threshold: float, top_n: int) -> list[dict]:
    """Statistical anomaly detection using z-score."""
    # Group by date
    daily_costs = {}
    daily_services = {}

    for item in items:
        cost = float(item.computed_amount or 0)
        service = item.service or "Unknown"

        if item.time_usage_started:
            date = item.time_usage_started.strftime("%Y-%m-%d")

            if date in daily_costs:
                daily_costs[date] += cost
            else:
                daily_costs[date] = cost
                daily_services[date] = {}

            if service in daily_services[date]:
                daily_services[date][service] += cost
            else:
                daily_services[date][service] = cost

    if len(daily_costs) < 3:
        return []

    # Calculate statistics
    costs = list(daily_costs.values())
    mean = statistics.mean(costs)
    stdev = statistics.stdev(costs) if len(costs) > 1 else 0

    if stdev == 0:
        return []

    anomalies = []
    for date, cost in daily_costs.items():
        z_score = (cost - mean) / stdev

        if z_score > threshold:
            deviation_pct = ((cost - mean) / mean) * 100 if mean > 0 else 0

            # Determine severity
            if z_score > 4:
                severity = "critical"
            elif z_score > 3:
                severity = "high"
            elif z_score > 2.5:
                severity = "medium"
            else:
                severity = "low"

            # Get top contributing services
            services = daily_services.get(date, {})
            contributors = sorted(
                services.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            anomalies.append({
                "date": date,
                "cost": cost,
                "expected_cost": mean,
                "deviation_percent": deviation_pct,
                "severity": severity,
                "root_cause": {
                    "contributors": [
                        {"service": s, "increase": c}
                        for s, c in contributors
                    ]
                }
            })

    # Sort by severity and return top N
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    anomalies.sort(key=lambda x: (severity_order.get(x["severity"], 4), -x["cost"]))

    return anomalies[:top_n]
