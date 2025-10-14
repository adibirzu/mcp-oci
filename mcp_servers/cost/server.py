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
from opentelemetry import trace

# MCP-OCI common imports
from mcp_oci_common import get_oci_config, get_compartment_id
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes

# FinOpsAI integration imports
from .finopsai.oci_client_adapter import make_clients, list_compartments_recursive
from .finopsai.templates import TEMPLATES
from .finopsai.schemas import (
    CostByCompartment, CostByTagOut, MonthlyTrend, ServiceDrilldown,
    BudgetStatusOut, SchedulesOut, ObjectStorageOut, FocusHealthOut, SpikesOut,
    UnitCostOut, ForecastCreditsOut
)
from .finopsai.tools.usage_queries import UsageQuery, request_summarized_usages
from .finopsai.utils import safe_float, currency_from, map_compartment_rows, resolve_tenancy
from .finopsai.tools.focus import list_focus_days

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

@app.tool("doctor", description="Return server health, config summary, and masking status")
def doctor() -> Dict[str, Any]:
    try:
        from mcp_oci_common.privacy import privacy_enabled
        cfg = get_oci_config()
        # Surface Usage API endpoint/region for diagnostics
        try:
            endpoint = getattr(clients.usage_api.base_client, 'endpoint', None)
        except Exception:
            endpoint = None
        # Best-effort tool listing without awaiting app coroutines
        try:
            from fastmcp.tools.tool import FunctionTool  # type: ignore
            tool_names = [n for n, v in globals().items() if isinstance(v, FunctionTool)]
        except Exception:
            tool_names = []
        return {
            "server": "oci-mcp-cost-enhanced",
            "ok": True,
            "privacy": bool(privacy_enabled()),
            "region": cfg.get("region"),
            "profile": os.getenv("OCI_PROFILE") or "DEFAULT",
            "tools": tool_names,
            "usage_api_endpoint": endpoint,
        }
    except Exception as e:
        return {"server": "oci-mcp-cost-enhanced", "ok": False, "error": str(e)}

@app.tool("healthcheck", description="Lightweight readiness/liveness check for the cost server")
def healthcheck() -> Dict[str, Any]:
    return {"status": "ok", "server": "oci-mcp-cost-enhanced", "pid": os.getpid()}

def _safe_serialize(obj) -> Dict[str, Any]:
    """Safely serialize objects with fallbacks for complex types"""
    try:
        # Try Pydantic model_dump first
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        # Try old Pydantic dict method
        elif hasattr(obj, 'dict'):
            return obj.dict()
        # Try direct dict conversion
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        # Return as-is if it's already a dict/primitive
        else:
            return obj
    except Exception as e:
        return {"serialization_error": str(e), "original_type": str(type(obj))}

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
        # Usage API requires home-region endpoint for many operations
        idc = oci.identity.IdentityClient(config)
        # Discover home region via home_region_key -> list_regions mapping (with subscription fallback)
        usage_cfg = dict(config)
        try:
            ten = usage_cfg.get("tenancy")
            if ten:
                ten_data = idc.get_tenancy(ten).data
                hr_key = getattr(ten_data, 'home_region_key', None)
                if hr_key:
                    regs = idc.list_regions().data or []
                    for r in regs:
                        if getattr(r, 'key', None) == hr_key:
                            usage_cfg['region'] = getattr(r, 'name', usage_cfg.get('region'))
                            break
                if 'region' not in usage_cfg or usage_cfg['region'] == config.get('region'):
                    subs = idc.list_region_subscriptions(ten)
                    for s in getattr(subs, 'data', []) or []:
                        if getattr(s, 'is_home_region', False):
                            usage_cfg['region'] = getattr(s, 'region_name', None) or getattr(s, 'region', usage_cfg.get('region'))
                            break
        except Exception:
            pass
        usage_client = oci.usage_api.UsageapiClient(usage_cfg)
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
            currency = None
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
                group_by=["service", "compartmentName"],
                compartment_depth=10  # required when grouping by compartment
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

# Helper: scope to compartments (single or children)
def _resolve_scope_compartments(scope_compartment_ocid: Optional[str], include_children: bool) -> Optional[List[str]]:
    """Resolve compartment scope for analysis.

    Accepts either a compartment OCID or a compartment name. If a name is provided,
    it is resolved to an OCID by searching compartments recursively.
    """
    if not scope_compartment_ocid:
        return None
    # If it's already an OCID, pass through
    if isinstance(scope_compartment_ocid, str) and scope_compartment_ocid.startswith("ocid1.compartment."):
        if include_children:
            tenancy = clients.config.get("tenancy")
            comps = list_compartments_recursive(clients.identity, tenancy, parent_compartment_id=scope_compartment_ocid)
            return [c["id"] for c in comps]
        return [scope_compartment_ocid]

    # Treat as compartment name: case-insensitive exact match preferred
    name = str(scope_compartment_ocid).strip()
    tenancy = clients.config.get("tenancy")
    all_comps = list_compartments_recursive(clients.identity, tenancy, parent_compartment_id=None) or []
    exact = [c for c in all_comps if str(c.get('name','')).lower() == name.lower()]
    chosen = exact[0] if exact else (all_comps[0] if all_comps else None)
    if not chosen:
        return None
    if include_children:
        comps = list_compartments_recursive(clients.identity, tenancy, parent_compartment_id=chosen['id'])
        return [c['id'] for c in comps]
    return [chosen['id']]

def _aggregate_usage_across_compartments(tenancy_ocid: str, comp_ids: List[str], base_query: UsageQuery) -> Dict[str, Any]:
    """Aggregate usage across multiple compartments"""
    import copy
    aggregate = {"items": [], "currency": "USD", "forecastItems": []}
    for cid in comp_ids:
        q = copy.deepcopy(base_query)
        # Narrow by compartmentId filter - ensure dimensions have proper structure
        filt = q.filter or {}

        # Create properly formatted dimension filter
        compartment_dimension = {
            "key": "compartmentId",
            "value": cid
        }

        # Handle existing dimensions
        dimensions = filt.get("dimensions", [])
        dimensions.append(compartment_dimension)

        # Create filter with proper operator and dimensions structure
        filt = {
            "operator": filt.get("operator", "AND"),
            "dimensions": dimensions
        }
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
        # Disable forecast at the query level to avoid regional Usage API validation errors
        # (e.g., forecast.timeForecastEnded must not be null). The request wrapper also includes
        # a forecast fallback, but this hard-disable ensures robust behavior.
        base_query = UsageQuery(
            granularity=granularity,
            time_start=time_usage_started,
            time_end=time_usage_ended,
            group_by=["compartmentName", "service"],
            forecast=False,
            # compartmentDepth must be <= 7 per Usage API validation
            compartment_depth=min(max(int(compartment_depth or 7), 1), 7)
        )

        # Validate tenancy OCID; fallback to config tenancy if malformed
        def _valid_ten(ocid: Optional[str]) -> bool:
            return bool(ocid and isinstance(ocid, str) and ocid.startswith("ocid1.tenancy.") and len(ocid) > 24 and "..." not in ocid)
        ten = tenancy_ocid if _valid_ten(tenancy_ocid) else clients.config.get("tenancy")

        comp_ids = _resolve_scope_compartments(scope_compartment_ocid, include_children)
        raw = _aggregate_usage_across_compartments(ten, comp_ids, base_query) if comp_ids else request_summarized_usages(clients, ten, base_query)

        # Build rows (date, compartment, service, cost) to match schema
        rows = map_compartment_rows(raw.get("items", []))

        currency = currency_from(raw)
        forecast = None
        if include_forecast and raw.get("forecastItems"):
            fa = sum(safe_float(f.get("computedAmount") or f.get("computed_amount")) for f in raw.get("forecastItems", []))
            forecast = {"amount": fa, "currency": currency}

        out = CostByCompartment(
            window={"start": time_usage_started, "end": time_usage_ended},
            currency=currency,
            rows=rows,
            forecast=forecast,
        )
        time_start = time_usage_started.split('T')[0] if 'T' in time_usage_started else time_usage_started
        time_end = time_usage_ended.split('T')[0] if 'T' in time_usage_ended else time_usage_ended
        return _envelope(f"Daily costs for {time_start} → {time_end} (scope={scope_compartment_ocid or 'tenancy'}).", _safe_serialize(out))

@app.tool("service_cost_drilldown", description="Top services by cost and their top compartments (supports scoped traversal)")
def service_cost_drilldown(tenancy_ocid: str, time_start: str, time_end: str, top_n: int = 10,
                          scope_compartment_ocid: Optional[str] = None, include_children: bool = False) -> Dict[str, Any]:
    """Advanced service cost drilldown with compartment scoping"""
    with tool_span(tracer, "service_cost_drilldown", mcp_server="oci-mcp-cost-enhanced") as span:
        # Validate tenancy OCID strictly; fallback to config tenancy if malformed
        ten = resolve_tenancy(tenancy_ocid, clients.config)
        base = UsageQuery(granularity="DAILY", time_start=time_start, time_end=time_end, group_by=["service"])
        comp_ids = _resolve_scope_compartments(scope_compartment_ocid, include_children)
        try:
            raw1 = _aggregate_usage_across_compartments(ten, comp_ids, base) if comp_ids else request_summarized_usages(clients, ten, base)
        except oci.exceptions.ServiceError as e:
            # Enrich error with discovered home region and guidance
            usage_region = getattr(getattr(clients.usage_api, 'base_client', None), 'region', None)
            usage_endpoint = getattr(getattr(clients.usage_api, 'base_client', None), 'endpoint', None)
            guidance = {
                "hint": "Usage API must be called in the tenancy home region and with tenantId=tenancy OCID",
                "used_tenancy": ten,
                "usage_api_region": usage_region,
                "usage_api_endpoint": usage_endpoint,
                "time_window": {"start": time_start, "end": time_end}
            }
            return _envelope("Usage API call failed.", {"error": str(e), "details": guidance})
        totals = {}
        for it in raw1.get("items", []):
            svc = it.get("service", "Unknown")
            # Handle both possible field names for computed amount
            try:
                amt = float(it.get("computedAmount") or it.get("computed_amount") or 0)
            except Exception:
                amt = 0.0
            totals[svc] = totals.get(svc, 0) + amt

        # Top services
        sorted_services = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # For each top service, get compartment breakdown
        services_detail = []
        for svc_name, svc_total in sorted_services:
            base2 = UsageQuery(granularity="DAILY", time_start=time_start, time_end=time_end,
                              group_by=["compartmentName"],
                              filter={"operator": "AND", "dimensions": [{"key": "service", "value": svc_name}]})
            raw2 = _aggregate_usage_across_compartments(ten, comp_ids, base2) if comp_ids else request_summarized_usages(clients, ten, base2)

            comp_breakdown = {}
            for it in raw2.get("items", []):
                comp = it.get("compartmentName", "Unknown")
                # Handle both possible field names for computed amount
                try:
                    amt = float(it.get("computedAmount") or it.get("computed_amount") or 0)
                except Exception:
                    amt = 0.0
                comp_breakdown[comp] = comp_breakdown.get(comp, 0) + amt

            # Top compartments for this service
            top_comps = sorted(comp_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]
            services_detail.append({
                "service": svc_name,
                "total": svc_total,
                "top_compartments": [{"name": c[0], "cost": c[1]} for c in top_comps],
                # Preserve tenancy currency from Usage API; avoid defaulting to USD
                "currency": raw1.get("currency") or raw2.get("currency")
            })

        # Convert to schema: top: List[TopService] with compartments entries
        top_list = []
        for svc in services_detail:
            comps = [
                {"name": c[0], "cost": float(c[1])}
                for c in sorted(((e["name"], e["cost"]) if isinstance(e, dict) else e for e in svc.get("top_compartments", [])), key=lambda x: -x[1])
            ]
            top_list.append({"service": svc.get("service"), "total": float(svc.get("total") or 0), "compartments": comps})

        out = ServiceDrilldown(
            window={"start": time_start, "end": time_end},
            top=top_list,
        )
        return _envelope("Top services and compartments computed.", _safe_serialize(out))

@app.tool("cost_by_tag_key_value", description="Cost rollups by a defined tag with service split (supports scoped traversal)")
def cost_by_tag_key_value(tenancy_ocid: str, time_start: str, time_end: str, defined_tag_ns: str, defined_tag_key: str, defined_tag_value: str, scope_compartment_ocid: str | None = None, include_children: bool = False) -> Dict[str, Any]:
    """Cost rollups by a defined tag with service split (supports scoped traversal)"""
    with tool_span(tracer, "cost_by_tag_key_value", mcp_server="oci-mcp-cost-enhanced") as span:
        q = UsageQuery(
            granularity="DAILY",
            time_start=time_start,
            time_end=time_end,
            group_by=None,  # Must be null when group_by_tag is used
            group_by_tag=[{"namespace": defined_tag_ns, "key": defined_tag_key}],
            filter={"tags": [{"namespace": defined_tag_ns, "key": defined_tag_key, "value": defined_tag_value}]},
        )
        comp_ids = _resolve_scope_compartments(scope_compartment_ocid, include_children)
        raw = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, q) if comp_ids else request_summarized_usages(clients, tenancy_ocid, q)
        # Preserve tenancy currency as reported by Usage API
        currency = currency_from(raw)
        services = {}
        total = 0.0
        for it in raw.get("items", []):
            cost = safe_float(it.get("computedAmount") or it.get("computed_amount"))
            svc = it.get("service", "")
            services[svc] = services.get(svc, 0.0) + cost
            total += cost
        out = CostByTagOut(tag={"ns": defined_tag_ns, "key": defined_tag_key, "value": defined_tag_value}, currency=currency, services=[{"service": k, "cost": v} for k, v in sorted(services.items(), key=lambda x: -x[1])], total=total)
        return _envelope(f"Scoped tag cost from {time_start} to {time_end}.", _safe_serialize(out))

@app.tool("monthly_trend_forecast", description="Month-over-month trend with forecast and optional budget variance")
def monthly_trend_forecast(tenancy_ocid: str, months_back: int = 6, budget_ocid: Optional[str] = None) -> Dict[str, Any]:
    """Advanced monthly trend analysis with forecasting"""
    with tool_span(tracer, "monthly_trend_forecast", mcp_server="oci-mcp-cost-enhanced") as span:
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta

        now = datetime.now()

        # Calculate start date: first day of (current month - months_back)
        start_date = (now - relativedelta(months=months_back)).replace(day=1)
        time_start = start_date.strftime("%Y-%m-%d")

        # For MONTHLY granularity with forecast, end date must be first day of current/next month at midnight
        # Calculate first day of current month
        current_month_start = datetime(now.year, now.month, 1)
        time_end = current_month_start.strftime("%Y-%m-%d")

        # Validate date range
        if time_start >= time_end:
            raise ValueError(f"Invalid date range: {time_start} to {time_end}")
        q = UsageQuery(granularity="MONTHLY", time_start=time_start, time_end=time_end, forecast=True)
        raw = request_summarized_usages(clients, tenancy_ocid, q)
        series = []
        for it in raw.get("items", []):
            # Handle both possible field names from API response
            time_field = it.get("timeUsageStarted") or it.get("time_usage_started") or ""
            month_key = time_field[:7]  # YYYY-MM
            # Handle both possible field names for computed amount
            amt = safe_float(it.get("computedAmount") or it.get("computed_amount"))
            series.append({"month": month_key, "actual": amt})

        # Forecast
        forecast_amt = sum(safe_float(f.get("computedAmount") or f.get("computed_amount")) for f in raw.get("forecastItems", []))
        forecast_data = {"next_month": forecast_amt, "currency": raw.get("currency")} if forecast_amt else None

        # Budget variance
        budget_variance = None
        if budget_ocid:
            # TODO: Implement budget lookup - for now return placeholder
            budget_variance = {"status": "unknown", "message": "Budget lookup not implemented"}

        out = MonthlyTrend(series=series, forecast=forecast_data, budget=budget_variance)
        return _envelope("Monthly trend and forecast computed from Usage API.", _safe_serialize(out))

@app.tool("focus_etl_healthcheck", description="Verify FOCUS files presence and sizes for recent days")
def focus_etl_healthcheck(tenancy_ocid: str, days_back: int = 14) -> Dict[str, Any]:
    """FOCUS ETL health check for compliance reporting"""
    with tool_span(tracer, "focus_etl_healthcheck", mcp_server="oci-mcp-cost-enhanced") as span:
        days = list_focus_days(clients, tenancy_ocid, days_back)
        gaps = [d["date"] for d in days if not d["present"]]
        out = FocusHealthOut(days=days, gaps=gaps)
        return _envelope("Checked Object Storage for FOCUS partitions.", _safe_serialize(out))

@app.tool("budget_status_and_actions", description="List budgets and alert rules in a compartment; optional recursive children")
def budget_status_and_actions(compartment_ocid: str, recursive_children: bool = False) -> Dict[str, Any]:
    """List budgets and alert rules in a compartment; optional recursive children"""
    with tool_span(tracer, "budget_status_and_actions", mcp_server="oci-mcp-cost-enhanced") as span:
        from .finopsai.tools.budgets import list_budgets_and_rules
        budgets = list_budgets_and_rules(clients, compartment_ocid)
        out = BudgetStatusOut(budgets=budgets, compartment_ocid=compartment_ocid, recursive_children=recursive_children)
        return _envelope("Budget status and alert rules retrieved.", _safe_serialize(out))

@app.tool("schedule_report_create_or_list", description="List or create Usage API cost schedules")
def schedule_report_create_or_list(compartment_ocid: str, action: str = "LIST", schedule_payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """List or create Usage API cost schedules"""
    with tool_span(tracer, "schedule_report_create_or_list", mcp_server="oci-mcp-cost-enhanced") as span:
        import oci
        if action.upper() == "CREATE" and schedule_payload:
            details = oci.usage_api.models.CreateScheduleDetails(**schedule_payload)
            s = clients.usage_api.create_schedule(details).data
            schedules = [{"id": s.id, "name": s.name, "destination": s.result_location.target, "frequency": s.schedule_recurrences.split(" ")[0]}]
            out = SchedulesOut(action="CREATE", schedules=schedules)
            return _envelope("Created schedule.", _safe_serialize(out))
        sch = clients.usage_api.list_schedules(compartment_id=compartment_ocid).data
        schedules = [{"id": s.id, "name": s.name, "destination": s.result_location.target, "frequency": s.schedule_recurrences.split(" ")[0]} for s in sch]
        out = SchedulesOut(action="LIST", schedules=schedules)
        return _envelope("Listed schedules.", _safe_serialize(out))

@app.tool("object_storage_costs_and_tiering", description="Object Storage spend by bucket with lifecycle hints (supports scoped traversal)")
def object_storage_costs_and_tiering(tenancy_ocid: str, time_start: str, time_end: str, scope_compartment_ocid: str | None = None, include_children: bool = False) -> Dict[str, Any]:
    """Object Storage spend by bucket with lifecycle hints (supports scoped traversal)"""
    with tool_span(tracer, "object_storage_costs_and_tiering", mcp_server="oci-mcp-cost-enhanced") as span:
        q = UsageQuery(granularity="DAILY", time_start=time_start, time_end=time_end, group_by=["service", "resourceName"], filter={"operator": "AND", "dimensions": [{"key": "service", "value": "Object Storage"}]})
        comp_ids = _resolve_scope_compartments(scope_compartment_ocid, include_children)
        raw = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, q) if comp_ids else request_summarized_usages(clients, tenancy_ocid, q)
        buckets = {}
        for it in raw.get("items", []):
            bucket = it.get("resourceName", "") or "(unknown)"
            buckets[bucket] = buckets.get(bucket, 0.0) + float(it.get("computedAmount", 0.0))
        out_list = [{"name": name, "cost": cost, "hint": "Consider IA/Archive + lifecycle if low access"} for name, cost in sorted(buckets.items(), key=lambda x: -x[1])]
        out = ObjectStorageOut(buckets=out_list)
        return _envelope("Object Storage bucket cost summary.", _safe_serialize(out))

@app.tool("top_cost_spikes_explain", description="Find top day-over-day cost spikes and explain (supports scoped traversal)")
def top_cost_spikes_explain(tenancy_ocid: str, time_start: str, time_end: str, top_n: int = 5, scope_compartment_ocid: str | None = None, include_children: bool = False) -> Dict[str, Any]:
    """Find top day-over-day cost spikes and explain (supports scoped traversal)"""
    with tool_span(tracer, "top_cost_spikes_explain", mcp_server="oci-mcp-cost-enhanced") as span:
        base = UsageQuery(granularity="DAILY", time_start=time_start, time_end=time_end)
        comp_ids = _resolve_scope_compartments(scope_compartment_ocid, include_children)
        raw = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, base) if comp_ids else request_summarized_usages(clients, tenancy_ocid, base)
        day_sum = {}
        for it in raw.get("items", []):
            # Handle both possible field names from API response
            time_field = it.get("timeUsageStarted") or it.get("time_usage_started") or ""
            d = time_field[:10]
            day_sum[d] = day_sum.get(d, 0.0) + float(it.get("computedAmount", 0.0))
        days = sorted(day_sum.keys())
        spikes = []
        for i in range(1, len(days)):
            delta = day_sum[days[i]] - day_sum[days[i-1]]
            if delta > 0:
                spikes.append((days[i], delta))
        spikes = sorted(spikes, key=lambda x: -x[1])[:top_n]
        out_items = []
        for date_str, delta in spikes:
            q_explain = UsageQuery(granularity="DAILY", time_start=date_str, time_end=date_str, group_by=["service", "compartmentName"])
            raw2 = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, q_explain) if comp_ids else request_summarized_usages(clients, tenancy_ocid, q_explain)
            services, compartments = {}, {}
            for it in raw2.get("items", []):
                amt = float(it.get("computedAmount") or it.get("computed_amount", 0.0))
                services[it.get("service", "")] = services.get(it.get("service", ""), 0.0) + amt
                compartments[it.get("compartmentName", "")] = compartments.get(it.get("compartmentName", ""), 0.0) + amt
            out_items.append({
                "date": date_str,
                "delta": delta,
                "services": sorted(({"service": k, "cost": v} for k, v in services.items()), key=lambda x: -x["cost"]),
                "compartments": sorted(({"name": k, "cost": v} for k, v in compartments.items()), key=lambda x: -x["cost"]),
            })
        out = SpikesOut(spikes=out_items)
        return _envelope("Detected and explained top daily spikes.", _safe_serialize(out))

@app.tool("per_compartment_unit_cost", description="Unit economics by compartment with per-service unit mapping (supports scoped traversal)")
def per_compartment_unit_cost(tenancy_ocid: str, time_start: str, time_end: str, unit: str = "OCPU_HOUR", scope_compartment_ocid: str | None = None, include_children: bool = False) -> Dict[str, Any]:
    """Unit economics by compartment with per-service unit mapping (supports scoped traversal)"""
    with tool_span(tracer, "per_compartment_unit_cost", mcp_server="oci-mcp-cost-enhanced") as span:
        UNIT_MAP = {
            "OCPU_HOUR": {"services": ["Compute"], "unit_keys": ["OCPU Hour", "OCPU-Hours", "OCPU Hours"]},
            "GB_MONTH": {"services": ["Object Storage", "Block Volume", "File Storage"], "unit_keys": ["GB-Month", "GB Month", "GB Months", "GB-Months"]},
        }
        cfg = UNIT_MAP.get(unit.upper(), UNIT_MAP["OCPU_HOUR"])
        q = UsageQuery(granularity="DAILY", time_start=time_start, time_end=time_end, group_by=["compartmentName", "service"])
        comp_ids = _resolve_scope_compartments(scope_compartment_ocid, include_children)
        raw = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, q) if comp_ids else request_summarized_usages(clients, tenancy_ocid, q)
        rows_map = {}
        for it in raw.get("items", []):
            svc = it.get("service", "")
            if cfg["services"] and svc not in cfg["services"]:
                continue
            unit_desc = (it.get("unit") or it.get("usageUnit") or it.get("usageUnitDescription") or "").lower()
            # if unit string doesn't match, we still consider computedQuantity for supported services
            cmp = it.get("compartmentName") or it.get("compartmentId", "")
            amt = float(it.get("computedAmount") or it.get("computed_amount", 0.0))
            qty = float(it.get("computedQuantity", 0.0) or it.get("quantity", 0.0))
            r = rows_map.setdefault(cmp, {"cost": 0.0, "qty": 0.0})
            r["cost"] += amt
            r["qty"] += qty
        rows = []
        for cmp, r in rows_map.items():
            qty = r["qty"] if r["qty"] > 0 else 1.0
            rows.append({"compartment": cmp, "cost": r["cost"], "quantity": qty, "unitCost": r["cost"] / qty})
        out = UnitCostOut(unit=unit.upper(), rows=rows)
        return _envelope("Computed per-service unit costs per compartment.", _safe_serialize(out))

@app.tool("forecast_vs_universal_credits", description="Compare forecasted spend vs Universal Credits")
def forecast_vs_universal_credits(tenancy_ocid: str, months_ahead: int = 1, credits_committed: float | None = None) -> Dict[str, Any]:
    """Compare forecasted spend vs Universal Credits"""
    with tool_span(tracer, "forecast_vs_universal_credits", mcp_server="oci-mcp-cost-enhanced") as span:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        time_end = now.date().isoformat()
        time_start = f"{now.year-1}-01-01"
        q = UsageQuery(granularity="MONTHLY", time_start=time_start, time_end=time_end, forecast=True)
        raw = request_summarized_usages(clients, tenancy_ocid, q)
        def _sf2(v):
            try:
                return float(v or 0)
            except Exception:
                return 0.0
        forecast_amt = 0.0
        if raw.get("forecastItems"):
            forecast_amt = sum(_sf2(x.get("computedAmount") or x.get("computed_amount")) for x in raw["forecastItems"])
        risk = "NEUTRAL"
        notes = []
        if credits_committed is not None:
            if forecast_amt > credits_committed * 1.05:
                risk = "OVER"; notes.append("Forecast exceeds committed credits by >5%.")
            elif forecast_amt < credits_committed * 0.85:
                risk = "UNDER"; notes.append("Forecast under-consuming credits by >15%.")
        out = ForecastCreditsOut(forecast={"monthsAhead": months_ahead, "amount": forecast_amt}, credits={"present": credits_committed is not None, "committed": credits_committed or 0.0}, risk=risk, notes=notes)
        return _envelope("Compared forecast vs. Universal Credits.", _safe_serialize(out))

@app.tool("templates", description="List available FinopsAI templates and their input contracts")
def list_templates() -> Dict[str, Any]:
    """List available FinOpsAI templates and their input contracts"""
    return TEMPLATES

# Helper defined earlier via utils.resolve_compartments

# Register existing MCP-OCI tools
app.add_tool(Tool.from_function(get_cost_summary, name="get_cost_summary", description="Get cost summary for specified time window"))
app.add_tool(Tool.from_function(get_usage_breakdown, name="get_usage_breakdown", description="Get detailed usage breakdown by service"))
app.add_tool(Tool.from_function(detect_cost_anomaly, name="detect_cost_anomaly", description="Detect cost anomalies in time series data"))

if __name__ == "__main__":
    # Start HTTP server for Prometheus metrics (non-blocking) - before app.run()
    try:
        from prometheus_client import start_http_server as _start_http_server
        port = int(os.getenv("METRICS_PORT", "8005"))
        logging.info(f"Starting Prometheus metrics server on port {port}")
        _start_http_server(port)
        logging.info(f"Prometheus metrics server started successfully on port {port}")
    except ImportError as e:
        logging.warning(f"prometheus_client not available: {e}")
    except Exception as e:
        logging.warning(f"Failed to start metrics server: {e}")

    app.run()
