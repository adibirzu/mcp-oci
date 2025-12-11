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
from mcp_oci_common import get_oci_config, get_compartment_id, validate_and_log_tools
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes
from mcp_oci_common.session import get_client
from mcp_oci_common.cache import get_cache
from mcp_oci_common.local_cache import get_local_cache

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

# Initialize FinOpsAI clients lazily
_clients = None

def get_clients():
    """Get or create FinOpsAI clients lazily"""
    global _clients
    if _clients is None:
        _clients = make_clients()
    return _clients

# Create FastMCP app
app = FastMCP("oci-mcp-cost-enhanced")


# =============================================================================
# Server Manifest Resource
# =============================================================================

@app.resource("server://manifest")
def server_manifest() -> str:
    """
    Server manifest resource for capability discovery.
    
    Returns server metadata, available skills, and tool categorization.
    MCP clients can cache this to reduce repeated tool discovery calls.
    """
    import json
    manifest = {
        "name": "OCI MCP Server",
        "version": "2.0.0",
        "description": "OCI Infrastructure MCP Server with cost analysis, inventory audit, and network diagnostics",
        "capabilities": {
            "skills": [
                "cost-analysis",
                "inventory-audit",
                "network-diagnostics"
            ],
            "tools": {
                "tier1_instant": [
                    "doctor",
                    "healthcheck",
                    "get_tenancy_info",
                    "get_cache_stats",
                    "list_templates"
                ],
                "tier2_api": [
                    "get_cost_summary",
                    "get_usage_breakdown",
                    "cost_by_compartment_daily",
                    "service_cost_drilldown",
                    "cost_by_tag_key_value",
                    "monthly_trend_forecast",
                    "budget_status_and_actions",
                    "schedule_report_create_or_list",
                    "object_storage_costs_and_tiering",
                    "top_cost_spikes_explain",
                    "per_compartment_unit_cost",
                    "forecast_vs_universal_credits",
                    "detect_cost_anomaly"
                ],
                "tier3_heavy": [
                    "focus_etl_healthcheck"
                ],
                "tier4_admin": [
                    "refresh_local_cache"
                ]
            }
        },
        "usage_guide": """
Start with Tier 1 tools for instant responses (< 100ms):
1. Use doctor() to verify configuration and masking status
2. Use healthcheck() for basic server status
3. Use get_tenancy_info() for tenancy overview
4. Use get_cache_stats() to check cache freshness

Then use Tier 2 tools for API-based analysis (1-10s):
1. Use get_cost_summary() for quick cost overview
2. Use service_cost_drilldown() for top services and compartments
3. Use monthly_trend_forecast() for trend analysis
4. Use top_cost_spikes_explain() to investigate anomalies

Skills provide high-level workflows:
- cost-analysis: Trend detection, anomaly identification, forecasting
- inventory-audit: Resource discovery, capacity planning, compliance
- network-diagnostics: Topology mapping, security assessment, connectivity
""",
        "environment_variables": [
            "OCI_PROFILE",
            "OCI_CONFIG_FILE",
            "OTEL_SERVICE_NAME",
            "METRICS_PORT",
            "DEBUG"
        ]
    }
    return json.dumps(manifest, indent=2)


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
            endpoint = getattr(get_clients().usage_api.base_client, 'endpoint', None)
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

@app.tool("get_tenancy_info", description="Get comprehensive tenancy information including home region, subscribed regions, and resource counts from local cache")
def get_tenancy_info() -> Dict[str, Any]:
    """Get comprehensive tenancy information with local cache enrichment"""
    with tool_span(tracer, "get_tenancy_info", mcp_server="oci-mcp-cost-enhanced") as span:
        try:
            local_cache = get_local_cache()

            # Get tenancy details from cache
            tenancy_details = local_cache.get_tenancy_details()
            cache_stats = local_cache.get_cache_statistics()

            # Also get live tenancy data from OCI
            cfg = get_oci_config()
            identity_client = get_client(oci.identity.IdentityClient)

            live_tenancy = identity_client.get_tenancy(cfg.get('tenancy')).data

            result = {
                'tenancy': {
                    'id': live_tenancy.id,
                    'name': live_tenancy.name,
                    'description': live_tenancy.description,
                    'home_region': tenancy_details.get('home_region'),
                    'subscribed_regions': tenancy_details.get('subscribed_regions', [])
                },
                'cache_info': {
                    'available': cache_stats.get('available', False),
                    'age_minutes': cache_stats.get('age_minutes'),
                    'needs_refresh': cache_stats.get('needs_refresh', True),
                    'resource_counts': cache_stats.get('resources', {})
                },
                'current_region': cfg.get('region'),
                'profile': os.getenv('OCI_PROFILE', 'DEFAULT')
            }

            return _envelope(
                f"Tenancy: {live_tenancy.name} (Home: {tenancy_details.get('home_region', 'N/A')})",
                result
            )

        except Exception as e:
            logging.error(f"Error getting tenancy info: {e}")
            span.record_exception(e)
            return _envelope("Error retrieving tenancy information", {'error': str(e)})

@app.tool("get_cache_stats", description="Get local cache statistics including age, resource counts, and refresh status")
def get_cache_stats() -> Dict[str, Any]:
    """Get local cache statistics"""
    with tool_span(tracer, "get_cache_stats", mcp_server="oci-mcp-cost-enhanced") as span:
        try:
            local_cache = get_local_cache()
            stats = local_cache.get_cache_statistics()

            return _envelope(
                f"Cache age: {stats.get('age_minutes', 0):.1f} minutes, Resources: {sum(stats.get('resources', {}).values())}",
                stats
            )

        except Exception as e:
            logging.error(f"Error getting cache stats: {e}")
            span.record_exception(e)
            return _envelope("Error retrieving cache statistics", {'error': str(e)})

@app.tool("refresh_local_cache", description="Trigger a refresh of the local resource cache (runs build-local-cache.py)")
def refresh_local_cache() -> Dict[str, Any]:
    """Trigger local cache refresh"""
    with tool_span(tracer, "refresh_local_cache", mcp_server="oci-mcp-cost-enhanced") as span:
        try:
            import subprocess
            import sys

            # Get script path
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'scripts',
                'build-local-cache.py'
            )

            if not os.path.exists(script_path):
                return _envelope(
                    "Cache builder script not found",
                    {'error': f'Script not found at {script_path}'}
                )

            # Run the cache builder
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                # Reload cache
                from mcp_oci_common.local_cache import reload_cache
                reload_cache()

                local_cache = get_local_cache()
                stats = local_cache.get_cache_statistics()

                return _envelope(
                    f"Cache refreshed successfully. Resources: {sum(stats.get('resources', {}).values())}",
                    {
                        'success': True,
                        'output': result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
                        'cache_stats': stats
                    }
                )
            else:
                return _envelope(
                    "Cache refresh failed",
                    {
                        'success': False,
                        'error': result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
                    }
                )

        except subprocess.TimeoutExpired:
            return _envelope(
                "Cache refresh timed out",
                {'error': 'Cache refresh exceeded 5 minute timeout'}
            )
        except Exception as e:
            logging.error(f"Error refreshing cache: {e}")
            span.record_exception(e)
            return _envelope("Error refreshing cache", {'error': str(e)})

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

def _fetch_cost_summary(
    time_window: str = "7d",
    granularity: str = "DAILY",
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
):
    config = get_oci_config()
    if region:
        config['region'] = region
    # Usage API requires home-region endpoint for many operations
    idc = get_client(oci.identity.IdentityClient, region=config.get("region"))
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
    usage_client = get_client(oci.usage_api.UsageapiClient, region=usage_cfg.get('region', config.get("region")))
    compartment = compartment_id or get_compartment_id()

    endpoint = usage_client.base_client.endpoint or ""
    add_oci_call_attributes(
        None,  # No span in internal
        oci_service="Usage API",
        oci_operation="RequestSummarizedUsages",
        region=config.get("region"),
        endpoint=endpoint,
    )

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7) if time_window == "7d" else end_time - timedelta(days=30)

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
        },
        'items_count': len(items)
    }, req_id

def get_cost_summary(
    time_window: str = "7d",
    granularity: str = "DAILY",
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict:
    """Get cost summary (existing MCP-OCI functionality)"""
    with tool_span(tracer, "get_cost_summary", mcp_server="oci-mcp-cost-enhanced") as span:
        cache = get_cache()
        params = {'time_window': time_window, 'granularity': granularity, 'compartment_id': compartment_id, 'region': region}
        try:
            summary, req_id = cache.get_or_refresh(
                server_name="oci-mcp-cost-enhanced",
                operation="get_cost_summary",
                params=params,
                fetch_func=lambda: _fetch_cost_summary(time_window, granularity, compartment_id, region),
                ttl_seconds=300,
                force_refresh=False
            )
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            span.set_attribute("items.count", summary.get('items_count', 0))
            return summary
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting cost summary: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def _fetch_usage_breakdown(
    service: Optional[str] = None,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
):
    config = get_oci_config()
    if region:
        config['region'] = region
    usage_client = get_client(oci.usage_api.UsageapiClient, region=config.get("region"))
    compartment = compartment_id or get_compartment_id()

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=30)

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

    return breakdown, req_id

def get_usage_breakdown(
    service: Optional[str] = None,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> List[Dict]:
    """Get usage breakdown by service (existing MCP-OCI functionality)"""
    with tool_span(tracer, "get_usage_breakdown", mcp_server="oci-mcp-cost-enhanced") as span:
        cache = get_cache()
        params = {'service': service, 'compartment_id': compartment_id, 'region': region}
        try:
            breakdown, req_id = cache.get_or_refresh(
                server_name="oci-mcp-cost-enhanced",
                operation="get_usage_breakdown",
                params=params,
                fetch_func=lambda: _fetch_usage_breakdown(service, compartment_id, region),
                ttl_seconds=300,
                force_refresh=False
            )
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            span.set_attribute("items.count", len(breakdown))
            if service:
                span.set_attribute("service", service)
            if compartment_id:
                span.set_attribute("compartment_id", compartment_id)
            if region:
                span.set_attribute("region", region)
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
            tenancy = get_clients().config.get("tenancy")
            comps = list_compartments_recursive(get_clients().identity, tenancy, parent_compartment_id=scope_compartment_ocid)
            return [c["id"] for c in comps]
        return [scope_compartment_ocid]

    # Treat as compartment name: case-insensitive exact match preferred
    name = str(scope_compartment_ocid).strip()
    tenancy = get_clients().config.get("tenancy")
    all_comps = list_compartments_recursive(get_clients().identity, tenancy, parent_compartment_id=None) or []
    exact = [c for c in all_comps if str(c.get('name','')).lower() == name.lower()]
    chosen = exact[0] if exact else (all_comps[0] if all_comps else None)
    if not chosen:
        return None
    if include_children:
        comps = list_compartments_recursive(get_clients().identity, tenancy, parent_compartment_id=chosen['id'])
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
        raw = request_summarized_usages(get_clients(), tenancy_ocid, q)
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
        ten = tenancy_ocid if _valid_ten(tenancy_ocid) else get_clients().config.get("tenancy")

        comp_ids = _resolve_scope_compartments(scope_compartment_ocid, include_children)
        raw = _aggregate_usage_across_compartments(ten, comp_ids, base_query) if comp_ids else request_summarized_usages(get_clients(), ten, base_query)

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
        ten = resolve_tenancy(tenancy_ocid, get_clients().config)
        base = UsageQuery(granularity="DAILY", time_start=time_start, time_end=time_end, group_by=["service"])
        comp_ids = _resolve_scope_compartments(scope_compartment_ocid, include_children)
        try:
            raw1 = _aggregate_usage_across_compartments(ten, comp_ids, base) if comp_ids else request_summarized_usages(get_clients(), ten, base)
        except oci.exceptions.ServiceError as e:
            # Enrich error with discovered home region and guidance
            usage_region = getattr(getattr(get_clients().usage_api, 'base_client', None), 'region', None)
            usage_endpoint = getattr(getattr(get_clients().usage_api, 'base_client', None), 'endpoint', None)
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
            raw2 = _aggregate_usage_across_compartments(ten, comp_ids, base2) if comp_ids else request_summarized_usages(get_clients(), ten, base2)

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
        raw = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, q) if comp_ids else request_summarized_usages(get_clients(), tenancy_ocid, q)
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
        raw = request_summarized_usages(get_clients(), tenancy_ocid, q)
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
        days = list_focus_days(get_clients(), tenancy_ocid, days_back)
        gaps = [d["date"] for d in days if not d["present"]]
        out = FocusHealthOut(days=days, gaps=gaps)
        return _envelope("Checked Object Storage for FOCUS partitions.", _safe_serialize(out))

@app.tool("budget_status_and_actions", description="List budgets and alert rules in a compartment; optional recursive children")
def budget_status_and_actions(compartment_ocid: str, recursive_children: bool = False) -> Dict[str, Any]:
    """List budgets and alert rules in a compartment; optional recursive children"""
    with tool_span(tracer, "budget_status_and_actions", mcp_server="oci-mcp-cost-enhanced") as span:
        from .finopsai.tools.budgets import list_budgets_and_rules
        budgets = list_budgets_and_rules(get_clients(), compartment_ocid)
        out = BudgetStatusOut(budgets=budgets, compartment_ocid=compartment_ocid, recursive_children=recursive_children)
        return _envelope("Budget status and alert rules retrieved.", _safe_serialize(out))

@app.tool("schedule_report_create_or_list", description="List or create Usage API cost schedules")
def schedule_report_create_or_list(compartment_ocid: str, action: str = "LIST", schedule_payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """List or create Usage API cost schedules"""
    with tool_span(tracer, "schedule_report_create_or_list", mcp_server="oci-mcp-cost-enhanced") as span:
        import oci
        if action.upper() == "CREATE" and schedule_payload:
            details = oci.usage_api.models.CreateScheduleDetails(**schedule_payload)
            s = get_clients().usage_api.create_schedule(details).data
            schedules = [{"id": s.id, "name": s.name, "destination": s.result_location.target, "frequency": s.schedule_recurrences.split(" ")[0]}]
            out = SchedulesOut(action="CREATE", schedules=schedules)
            return _envelope("Created schedule.", _safe_serialize(out))
        sch = get_clients().usage_api.list_schedules(compartment_id=compartment_ocid).data
        schedules = [{"id": s.id, "name": s.name, "destination": s.result_location.target, "frequency": s.schedule_recurrences.split(" ")[0]} for s in sch]
        out = SchedulesOut(action="LIST", schedules=schedules)
        return _envelope("Listed schedules.", _safe_serialize(out))

@app.tool("object_storage_costs_and_tiering", description="Object Storage spend by bucket with lifecycle hints (supports scoped traversal)")
def object_storage_costs_and_tiering(tenancy_ocid: str, time_start: str, time_end: str, scope_compartment_ocid: str | None = None, include_children: bool = False) -> Dict[str, Any]:
    """Object Storage spend by bucket with lifecycle hints (supports scoped traversal)"""
    with tool_span(tracer, "object_storage_costs_and_tiering", mcp_server="oci-mcp-cost-enhanced") as span:
        q = UsageQuery(granularity="DAILY", time_start=time_start, time_end=time_end, group_by=["service", "resourceName"], filter={"operator": "AND", "dimensions": [{"key": "service", "value": "Object Storage"}]})
        comp_ids = _resolve_scope_compartments(scope_compartment_ocid, include_children)
        raw = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, q) if comp_ids else request_summarized_usages(get_clients(), tenancy_ocid, q)
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
        raw = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, base) if comp_ids else request_summarized_usages(get_clients(), tenancy_ocid, base)
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
            raw2 = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, q_explain) if comp_ids else request_summarized_usages(get_clients(), tenancy_ocid, q_explain)
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
        raw = _aggregate_usage_across_compartments(tenancy_ocid, comp_ids, q) if comp_ids else request_summarized_usages(get_clients(), tenancy_ocid, q)
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
        raw = request_summarized_usages(get_clients(), tenancy_ocid, q)
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
                risk = "OVER"
                notes.append("Forecast exceeds committed credits by >5%.")
            elif forecast_amt < credits_committed * 0.85:
                risk = "UNDER"
                notes.append("Forecast under-consuming credits by >15%.")
        out = ForecastCreditsOut(forecast={"monthsAhead": months_ahead, "amount": forecast_amt}, credits={"present": credits_committed is not None, "committed": credits_committed or 0.0}, risk=risk, notes=notes)
        return _envelope("Compared forecast vs. Universal Credits.", _safe_serialize(out))

@app.tool("templates", description="List available FinopsAI templates and their input contracts")
def list_templates() -> Dict[str, Any]:
    """List available FinOpsAI templates and their input contracts"""
    return TEMPLATES


# =============================================================================
# Skill-Based Tools (High-Level Agent Operations)
# =============================================================================

@app.tool("skill_analyze_cost_trend", description="Analyze cost trends over time with forecasting and recommendations. Returns trend direction, change percentage, forecast, and actionable recommendations.")
def skill_analyze_cost_trend_tool(
    tenancy_ocid: str,
    months_back: int = 6,
    budget_ocid: Optional[str] = None
) -> Dict[str, Any]:
    """Skill: Analyze cost trends with forecasting"""
    try:
        from mcp_servers.skills.tools_skills import skill_analyze_cost_trend
        return skill_analyze_cost_trend(tenancy_ocid, months_back, budget_ocid)
    except Exception as e:
        return {"error": str(e)}


@app.tool("skill_detect_cost_anomalies", description="Detect cost anomalies and spikes with root cause explanations. Returns severity-classified anomalies with service/compartment breakdown.")
def skill_detect_cost_anomalies_tool(
    tenancy_ocid: str,
    time_start: str,
    time_end: str,
    threshold: float = 2.0,
    top_n: int = 10
) -> Dict[str, Any]:
    """Skill: Detect cost anomalies with explanations"""
    try:
        from mcp_servers.skills.tools_skills import skill_detect_cost_anomalies
        return skill_detect_cost_anomalies(tenancy_ocid, time_start, time_end, threshold, top_n)
    except Exception as e:
        return {"error": str(e)}


@app.tool("skill_get_service_breakdown", description="Get detailed service cost breakdown with optimization potential. Returns top services by cost with compartment details and recommendations.")
def skill_get_service_breakdown_tool(
    tenancy_ocid: str,
    time_start: str,
    time_end: str,
    top_n: int = 10
) -> Dict[str, Any]:
    """Skill: Get service cost breakdown"""
    try:
        from mcp_servers.skills.tools_skills import skill_get_service_breakdown
        return skill_get_service_breakdown(tenancy_ocid, time_start, time_end, top_n)
    except Exception as e:
        return {"error": str(e)}


@app.tool("skill_generate_cost_optimization_report", description="Generate comprehensive cost optimization report combining trend analysis, anomaly detection, service breakdown, and prioritized recommendations.")
def skill_generate_cost_optimization_report_tool(
    tenancy_ocid: str,
    days_back: int = 30
) -> Dict[str, Any]:
    """Skill: Generate full cost optimization report"""
    try:
        from mcp_servers.skills.tools_skills import skill_generate_cost_optimization_report
        return skill_generate_cost_optimization_report(tenancy_ocid, days_back)
    except Exception as e:
        return {"error": str(e)}


# Helper defined earlier via utils.resolve_compartments

# Register existing MCP-OCI tools
app.add_tool(Tool.from_function(get_cost_summary, name="get_cost_summary", description="Get cost summary for specified time window"))
app.add_tool(Tool.from_function(get_usage_breakdown, name="get_usage_breakdown", description="Get detailed usage breakdown by service"))
app.add_tool(Tool.from_function(detect_cost_anomaly, name="detect_cost_anomaly", description="Detect cost anomalies in time series data"))

if __name__ == "__main__":
    # Validate MCP tool names at startup
    tool_names = [
        "doctor",
        "healthcheck",
        "get_tenancy_info",
        "get_cache_stats",
        "refresh_local_cache",
        "cost_by_compartment_daily",
        "service_cost_drilldown",
        "cost_by_tag_key_value",
        "monthly_trend_forecast",
        "focus_etl_healthcheck",
        "budget_status_and_actions",
        "schedule_report_create_or_list",
        "object_storage_costs_and_tiering",
        "top_cost_spikes_explain",
        "per_compartment_unit_cost",
        "forecast_vs_universal_credits",
        "templates",
        "get_cost_summary",
        "get_usage_breakdown",
        "detect_cost_anomaly"
    ]
    validation_entries = [{"name": name} for name in tool_names]
    if not validate_and_log_tools(validation_entries, "oci-mcp-cost"):
        logging.error("MCP tool validation failed. Server will not start.")
        exit(1)

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
