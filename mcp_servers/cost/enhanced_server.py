"""
Enhanced OCI Cost Server with FinOpsAI Integration
Combines the existing MCP-OCI cost server with advanced FinOpsAI analytics tools
"""
import os
import logging
import oci
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import numpy as np
from scipy import stats
from fastmcp import FastMCP
from fastmcp.tools import Tool
from mcp_oci_common.otel import trace

# MCP-OCI common imports
from mcp_oci_common import get_oci_config, get_compartment_id
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes

# FinOpsAI integration imports
from finopsai.oci_client_adapter import make_clients, list_compartments_recursive
from finopsai.templates import TEMPLATES
from finopsai.schemas import (
    CostByCompartment, MonthlyTrend, ServiceDrilldown,
    FocusHealthOut
)
from finopsai.tools.usage_queries import UsageQuery, request_summarized_usages
from finopsai.tools.focus import list_focus_days

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing with proper Resource
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-cost-enhanced")
init_tracing(service_name="oci-mcp-cost-enhanced")
init_metrics()
tracer = trace.get_tracer("oci-mcp-cost-enhanced")

# Initialize FinOpsAI clients
clients = make_clients()

# Create FastMCP app
app = FastMCP("oci-mcp-cost-enhanced")

def _envelope(human: str, machine: Any) -> Dict[str, Any]:
    """Envelope response with summary and data"""
    return {"summary": human, "data": machine}

# ===== EXISTING MCP-OCI COST TOOLS =====

def get_cost_summary(
    time_window: str = "7d",
    granularity: str = "DAILY",
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict:
    """Get cost summary (existing MCP-OCI functionality)"""
    with tool_span(tracer, "get_cost_summary", mcp_server="oci-mcp-cost-enhanced") as span:
        config = get_oci_config()
        if region:
            config['region'] = region
        usage_client = oci.usage_api.UsageapiClient(config)
        compartment = compartment_id or get_compartment_id()

        endpoint = usage_client.base_client.endpoint or ""
        add_oci_call_attributes(
            span,
            oci_service="Usage API",
            oci_operation="RequestSummarizedUsages",
            region=config.get("region"),
            endpoint=endpoint,
        )

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7) if time_window == "7d" else end_time - timedelta(days=30)

        try:
            details = oci.usage_api.models.RequestSummarizedUsagesDetails(
                tenant_id=config.get("tenancy"),
                time_usage_started=start_time.replace(hour=0, minute=0, second=0, microsecond=0),
                time_usage_ended=end_time.replace(hour=0, minute=0, second=0, microsecond=0),
                granularity=granularity.upper(),
                query_type="COST"
            )
            response = usage_client.request_summarized_usages(
                request_summarized_usages_details=details
            )
            req_id = getattr(response, "headers", {}).get("opc-request-id") if hasattr(response, "headers") else None
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            items = getattr(getattr(response, "data", None), "items", None) or []

            # Calculate total cost and extract currency information
            total = 0
            currency = "USD"  # Default fallback
            for item in items:
                amount = getattr(item, "computed_amount", 0) or 0
                total += amount
                # Extract currency from the first item that has it
                if hasattr(item, "currency") and getattr(item, "currency"):
                    currency = str(getattr(item, "currency")).strip()

            return {
                'total_cost': total,
                'currency': currency,
                'time_period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'granularity': granularity
                }
            }
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting cost summary: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def get_usage_breakdown(
    service: Optional[str] = None,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> List[Dict]:
    """Get usage breakdown by service (existing MCP-OCI functionality)"""
    with tool_span(tracer, "get_usage_breakdown", mcp_server="oci-mcp-cost-enhanced") as span:
        config = get_oci_config()
        if region:
            config['region'] = region
        usage_client = oci.usage_api.UsageapiClient(config)
        compartment = compartment_id or get_compartment_id()

        endpoint = usage_client.base_client.endpoint or ""
        add_oci_call_attributes(
            span,
            oci_service="Usage API",
            oci_operation="RequestSummarizedUsages",
            region=config.get("region"),
            endpoint=endpoint,
        )

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)

        try:
            details = oci.usage_api.models.RequestSummarizedUsagesDetails(
                tenant_id=config.get("tenancy"),
                time_usage_started=start_time.replace(hour=0, minute=0, second=0, microsecond=0),
                time_usage_ended=end_time.replace(hour=0, minute=0, second=0, microsecond=0),
                granularity="DAILY",
                query_type="COST",
                group_by=["service", "compartmentName"]
            )

            if service:
                # Add service filter
                details.filter = oci.usage_api.models.Filter(
                    operator="AND",
                    dimensions=[
                        oci.usage_api.models.Dimension(
                            key="service",
                            value=service
                        )
                    ]
                )

            response = usage_client.request_summarized_usages(
                request_summarized_usages_details=details
            )

            req_id = getattr(response, "headers", {}).get("opc-request-id") if hasattr(response, "headers") else None
            if req_id:
                span.set_attribute("oci.request_id", req_id)

            items = getattr(getattr(response, "data", None), "items", None) or []

            breakdown = []
            for item in items:
                breakdown.append({
                    'service': getattr(item, 'service', 'Unknown'),
                    'compartment': getattr(item, 'compartment_name', 'Unknown'),
                    'cost': getattr(item, 'computed_amount', 0),
                    'currency': getattr(item, 'currency', 'USD'),
                    'usage_start': str(getattr(item, 'time_usage_started', '')),
                    'usage_end': str(getattr(item, 'time_usage_ended', ''))
                })

            return breakdown
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting usage breakdown: {e}")
            span.record_exception(e)
            return []

def detect_cost_anomaly(
    series: List[float],
    method: str = "z_score",
    threshold: float = 2.0
) -> Dict:
    """Detect cost anomalies (existing MCP-OCI functionality)"""
    with tool_span(tracer, "detect_cost_anomaly", mcp_server="oci-mcp-cost-enhanced") as span:
        if len(series) < 3:
            return {'anomalies': [], 'method': method}

        anomalies = []
        if method == "z_score":
            z_scores = np.abs(stats.zscore(series))
            anomaly_indices = np.where(z_scores > threshold)[0]
            anomalies = [{'index': int(idx), 'value': series[idx], 'z_score': float(z_scores[idx])}
                        for idx in anomaly_indices]

        return {
            'anomalies': anomalies,
            'method': method,
            'threshold': threshold,
            'total_points': len(series)
        }

# ===== FINOPSAI ADVANCED TOOLS =====

@app.tool("templates", description="List available FinopsAI templates and their input contracts")
def list_templates() -> Dict[str, Any]:
    """List all available FinOpsAI analysis templates"""
    return TEMPLATES

# Helper: scope to compartments (single or children)
def _resolve_scope_compartments(scope_compartment_ocid: Optional[str], include_children: bool) -> Optional[List[str]]:
    """Resolve compartment scope for analysis"""
    if not scope_compartment_ocid:
        return None
    tenancy = clients.config.get("tenancy")
    comps = list_compartments_recursive(clients.identity, tenancy, parent_compartment_id=scope_compartment_ocid) if include_children else [{"id": scope_compartment_ocid}]
    return [c["id"] for c in comps]

def _aggregate_usage_across_compartments(tenancy_ocid: str, comp_ids: List[str], base_query: UsageQuery) -> Dict[str, Any]:
    """Aggregate usage across multiple compartments"""
    import copy
    aggregate = {"items": [], "currency": "USD", "forecastItems": []}
    for cid in comp_ids:
        q = copy.deepcopy(base_query)
        # Narrow by compartmentId filter
        filt = q.filter or {}
        # OCI filter schema varies; we attach a dimension filter pattern
        values = filt.get("dimensions", [])
        values.append({"dimensionKey": "compartmentId", "values": [cid]})
        filt["dimensions"] = values
        q.filter = filt
        raw = request_summarized_usages(clients, tenancy_ocid, q)
        # Merge
        aggregate["items"].extend(raw.get("items", []))
        aggregate["forecastItems"].extend(raw.get("forecastItems", []))
        # Currency from first non-empty
        if raw.get("currency") and not aggregate.get("currency"):
            aggregate["currency"] = raw["currency"]
    return aggregate

@app.tool("cost_by_compartment_daily", description="Daily cost by compartment & service with optional forecast and compartment traversal")
def cost_by_compartment_daily(tenancy_ocid: str, time_usage_started: str, time_usage_ended: str,
                             granularity: str = "DAILY", compartment_depth: int = 0, include_forecast: bool = True,
                             scope_compartment_ocid: Optional[str] = None, include_children: bool = False) -> Dict[str, Any]:
    """Daily cost analysis by compartment with advanced scoping"""
    with tool_span(tracer, "cost_by_compartment_daily", mcp_server="oci-mcp-cost-enhanced") as span:
        base_query = UsageQuery(granularity=granularity, time_start=time_usage_started, time_end=time_usage_ended,
                               group_by=["compartmentName", "service"], forecast=include_forecast)

        comp_ids = _resolve_scope_compartments(scope_compartment_ocid, include_children)
        raw = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, base_query) if comp_ids else request_summarized_usages(clients, tenancy_ocid, base_query)

        # Group by compartment+service for presentation
        groups = {}
        for item in raw.get("items", []):
            comp = item.get("compartmentName", "Unknown")
            svc = item.get("service", "Unknown")
            key = f"{comp}/{svc}"
            if key not in groups:
                groups[key] = {"compartment": comp, "service": svc, "total": 0.0, "currency": item.get("currency", "USD")}
            groups[key]["total"] += float(item.get("computedAmount", 0))

        compartments = list(groups.values())
        forecast = {"amount": sum(float(f.get("computedAmount", 0)) for f in raw.get("forecastItems", [])), "currency": raw.get("currency", "USD")}

        out = CostByCompartment(compartments=compartments, forecast=forecast if include_forecast else None, period={"start": time_usage_started, "end": time_usage_ended})
        time_start = time_usage_started.split('T')[0] if 'T' in time_usage_started else time_usage_started
        time_end = time_usage_ended.split('T')[0] if 'T' in time_usage_ended else time_usage_ended
        return _envelope(f"Daily costs for {time_start} → {time_end} (scope={scope_compartment_ocid or 'tenancy'}).", out.model_dump())

@app.tool("service_cost_drilldown", description="Top services by cost and their top compartments (supports scoped traversal)")
def service_cost_drilldown(tenancy_ocid: str, time_start: str, time_end: str, top_n: int = 10,
                          scope_compartment_ocid: Optional[str] = None, include_children: bool = False) -> Dict[str, Any]:
    """Advanced service cost drilldown with compartment scoping"""
    with tool_span(tracer, "service_cost_drilldown", mcp_server="oci-mcp-cost-enhanced") as span:
        base = UsageQuery(granularity="DAILY", time_start=time_start, time_end=time_end, group_by=["service"])
        comp_ids = _resolve_scope_compartments(scope_compartment_ocid, include_children)
        raw1 = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, base) if comp_ids else request_summarized_usages(clients, tenancy_ocid, base)
        totals = {}
        for it in raw1.get("items", []):
            svc = it.get("service", "Unknown")
            amt = float(it.get("computedAmount", 0))
            totals[svc] = totals.get(svc, 0) + amt

        # Top services
        sorted_services = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # For each top service, get compartment breakdown
        services_detail = []
        for svc_name, svc_total in sorted_services:
            base2 = UsageQuery(granularity="DAILY", time_start=time_start, time_end=time_end,
                              group_by=["compartmentName"],
                              filter={"operator": "AND", "dimensions": [{"dimensionKey": "service", "values": [svc_name]}]})
            raw2 = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, base2) if comp_ids else request_summarized_usages(clients, tenancy_ocid, base2)

            comp_breakdown = {}
            for it in raw2.get("items", []):
                comp = it.get("compartmentName", "Unknown")
                amt = float(it.get("computedAmount", 0))
                comp_breakdown[comp] = comp_breakdown.get(comp, 0) + amt

            # Top compartments for this service
            top_comps = sorted(comp_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]
            services_detail.append({
                "service": svc_name, "total": svc_total,
                "top_compartments": [{"name": c[0], "cost": c[1]} for c in top_comps],
                "currency": raw1.get("currency", "USD")
            })

        out = ServiceDrilldown(services=services_detail, period={"start": time_start, "end": time_end}, scope=scope_compartment_ocid)
        return _envelope("Top services and compartments computed.", out.model_dump())

@app.tool("monthly_trend_forecast", description="Month-over-month trend with forecast and optional budget variance")
def monthly_trend_forecast(tenancy_ocid: str, months_back: int = 6, budget_ocid: Optional[str] = None) -> Dict[str, Any]:
    """Advanced monthly trend analysis with forecasting"""
    with tool_span(tracer, "monthly_trend_forecast", mcp_server="oci-mcp-cost-enhanced") as span:
        now = datetime.now()
        start_month = now.month - months_back
        start_year = now.year
        if start_month <= 0:
            start_year += (start_month - 1) // 12
            start_month = start_month % 12 + 12 * (start_month <= 0)
        time_start = f"{start_year:04d}-{start_month:02d}-01"
        q = UsageQuery(granularity="MONTHLY", time_start=time_start, time_end=now.strftime("%Y-%m-%d"), forecast=True)
        raw = request_summarized_usages(clients, tenancy_ocid, q)
        series = []
        for it in raw.get("items", []):
            month_key = (it.get("timeUsageStarted") or "")[:7]  # YYYY-MM
            amt = float(it.get("computedAmount", 0))
            series.append({"month": month_key, "cost": amt, "currency": it.get("currency", "USD")})

        # Calculate trend
        if len(series) >= 2:
            costs = [s["cost"] for s in series]
            trend = "UP" if costs[-1] > costs[-2] else "DOWN" if costs[-1] < costs[-2] else "FLAT"
            pct_change = ((costs[-1] - costs[-2]) / costs[-2] * 100) if costs[-2] != 0 else 0
        else:
            trend, pct_change = "UNKNOWN", 0

        # Forecast
        forecast_amt = sum(float(f.get("computedAmount", 0)) for f in raw.get("forecastItems", []))
        forecast_data = {"next_month": forecast_amt, "currency": raw.get("currency", "USD")} if forecast_amt else None

        # Budget variance
        budget_variance = None
        if budget_ocid:
            # TODO: Implement budget lookup - for now return placeholder
            budget_variance = {"status": "unknown", "message": "Budget lookup not implemented"}

        out = MonthlyTrend(series=series, trend=trend, trend_pct=pct_change, forecast=forecast_data, budget_variance=budget_variance)
        return _envelope("Monthly trend and forecast computed from Usage API.", out.model_dump())

@app.tool("focus_etl_healthcheck", description="Verify FOCUS files presence and sizes for recent days")
def focus_etl_healthcheck(tenancy_ocid: str, days_back: int = 14) -> Dict[str, Any]:
    """FOCUS ETL health check for compliance reporting"""
    with tool_span(tracer, "focus_etl_healthcheck", mcp_server="oci-mcp-cost-enhanced") as span:
        days = list_focus_days(clients, tenancy_ocid, days_back)
        gaps = [d["date"] for d in days if not d["present"]]
        out = FocusHealthOut(days=days, gaps=gaps)
        return _envelope("Checked Object Storage for FOCUS partitions.", out.model_dump())

# Register existing MCP-OCI tools
app.add_tool(Tool.from_function(get_cost_summary, name="get_cost_summary", description="Get cost summary for specified time window"))
app.add_tool(Tool.from_function(get_usage_breakdown, name="get_usage_breakdown", description="Get detailed usage breakdown by service"))
app.add_tool(Tool.from_function(detect_cost_anomaly, name="detect_cost_anomaly", description="Detect cost anomalies in time series data"))

def main():
    """Main entry point for running the enhanced MCP server"""
    app.run()

if __name__ == "__main__":
    main()