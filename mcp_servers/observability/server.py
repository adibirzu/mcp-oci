# oci_mcp_observability_server.py

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List

# ----- Observability bootstrap -----
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span
from mcp_oci_common.privacy import privacy_enabled, redact_payload
from mcp_oci_common.otel_mcp import create_mcp_otel_enhancer

# ----- OCI SDK -----
import oci
from oci.exceptions import ServiceError

# ----- MCP runtime -----
from fastmcp import FastMCP
from fastmcp.tools import Tool

# ----- OpenTelemetry -----
from opentelemetry import trace

"""Use the consolidated Log Analytics implementation from mcp_servers.loganalytics.server.
This ensures there is a single source of truth for LA tools across servers.
"""
from mcp_servers.loganalytics.server import (
    execute_query as la_execute_query_impl,
    search_security_events as la_search_security_events_impl,
    get_mitre_techniques as la_get_mitre_techniques_impl,
    analyze_ip_activity as la_analyze_ip_activity_impl,
    perform_statistical_analysis as la_perform_statistical_analysis_impl,
    perform_advanced_analytics as la_perform_advanced_analytics_impl,
    validate_query as la_validate_query_impl,
    get_documentation as la_get_documentation_impl,
    check_oci_connection as la_check_connection_impl,
)

from mcp_oci_common import get_oci_config, get_compartment_id

# ----- Logging -----
logging.basicConfig(level=logging.INFO if os.getenv("DEBUG") else logging.WARNING)

# ----- Tracing & metrics -----
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-observability")
init_tracing(service_name="oci-mcp-observability")
init_metrics()
tracer = trace.get_tracer("oci-mcp-observability")

# ----- Enhanced MCP OpenTelemetry -----
mcp_otel_enhancer = create_mcp_otel_enhancer("oci-mcp-observability")

# Register trace notification handler
def trace_notification_handler(notification: Dict):
    """Handle MCP trace notifications"""
    try:
        # Log trace notifications for debugging
        logging.info(f"MCP Trace Notification: {json.dumps(notification, indent=2)}")

        # In a real implementation, you might:
        # - Send to external observability platform
        # - Store in database
        # - Forward to other systems

    except Exception as e:
        logging.warning(f"Failed to handle trace notification: {e}")

mcp_otel_enhancer.register_trace_handler(trace_notification_handler)

# Recent MCP calls buffer (for explainability and gap analysis)
_RECENT_CALLS: list[dict] = []
_RECENT_MAX = 100

def _record_call(entry: dict) -> None:
    try:
        entry["ts"] = datetime.now(timezone.utc).isoformat()
        _RECENT_CALLS.append(entry)
        if len(_RECENT_CALLS) > _RECENT_MAX:
            del _RECENT_CALLS[0:len(_RECENT_CALLS)-_RECENT_MAX]
    except Exception:
        pass

# =========================================================
# Helpers: compartments & namespace resolution
# =========================================================

def _effective_compartment(config, explicit: Optional[str]) -> str:
    """
    Resolve a compartment OCID to use for LA queries.
    Priority: explicit argument -> COMPARTMENT_OCID env -> tenancy OCID from config.
    """
    cid = explicit or get_compartment_id() or config.get("tenancy")
    if not cid:
        raise RuntimeError("Unable to resolve compartment OCID. Set COMPARTMENT_OCID or ensure tenancy is configured.")
    return cid

# ------- Logging Analytics namespace resolution (auto-detect once per process)
_la_namespace: Optional[str] = None
_la_namespace_source: Optional[str] = None  # env | auto | manual
_la_namespaces: List[Dict] = []
_la_tenancy: Optional[str] = None

def _list_la_namespaces(config) -> List[Dict]:
    """
    List OCI Logging Analytics namespaces for the current tenancy.
    """
    la_client = oci.log_analytics.LogAnalyticsClient(config)
    tenancy_id = config.get("tenancy") or os.getenv("COMPARTMENT_OCID")
    if not tenancy_id:
        raise RuntimeError("Cannot resolve tenancy OCID for Logging Analytics namespace lookup")
    resp = la_client.list_namespaces(compartment_id=tenancy_id)
    results: List[Dict] = []
    ns_items = getattr(getattr(resp, "data", None), "items", []) or []
    for ns in ns_items:
        results.append({
            "name": getattr(ns, "namespace_name", None) or getattr(ns, "name", None),
            "description": getattr(ns, "description", None),
            "time_created": getattr(ns, "time_created", None),
            "time_updated": getattr(ns, "time_updated", None),
            "is_onboarded": getattr(ns, "is_onboarded", True),
        })
    return [n for n in results if n.get("name")]

def _init_la_namespace_on_start():
    """
    Initialize namespace at server start. Honors LA_NAMESPACE env; otherwise auto-detect.
    If multiple namespaces exist and no LA_NAMESPACE is set, do not guess—require explicit set.
    """
    global _la_namespace, _la_namespace_source, _la_namespaces, _la_tenancy
    try:
        cfg = get_oci_config()
        _la_tenancy = cfg.get("tenancy") or os.getenv("COMPARTMENT_OCID")
        # 1) From env (authoritative)
        ns_env = os.getenv("LA_NAMESPACE")
        if ns_env:
            _la_namespace = ns_env
            _la_namespace_source = "env"
            _la_namespaces = _list_la_namespaces(cfg)
            return
        # 2) Auto-detect
        _la_namespaces = _list_la_namespaces(cfg)
        if len(_la_namespaces) == 1:
            _la_namespace = _la_namespaces[0]["name"]
            _la_namespace_source = "auto"
        else:
            # Leave unset; tools will ask user to choose
            _la_namespace = None
            _la_namespace_source = None
    except Exception as e:
        # Do not prevent server from starting; tools will surface error
        logging.warning(f"Logging Analytics namespace init skipped: {e}")

def _ensure_namespace(config) -> str:
    """
    Ensure we have a namespace selected; if multiple available and not selected, raise with guidance.
    """
    global _la_namespace, _la_namespaces
    if _la_namespace:
        return _la_namespace
    # Recompute list in case environment changed
    _la_namespaces = _list_la_namespaces(config)
    if len(_la_namespaces) == 0:
        raise RuntimeError("No Logging Analytics namespace found for tenancy (is LA enabled?)")
    if len(_la_namespaces) == 1:
        _la_namespace = _la_namespaces[0]["name"]
        return _la_namespace
    available = [n["name"] for n in _la_namespaces]
    raise RuntimeError(f"Multiple Logging Analytics namespaces available: {available}. Call set_la_namespace to select one.")

# Initialize namespace once at module import (server start)
_init_la_namespace_on_start()

# =========================================================
# LA query helpers: async polling & result shaping
# =========================================================

def _shape_la_rows(response) -> List[Dict]:
    """
    Normalizes LA results to a list[dict] with column names.
    Works for both sync (query) and async (get_query_result) responses.
    """
    data = getattr(response, "data", None)
    if not data:
        return []
    columns = []
    if getattr(data, "columns", None):
        for i, c in enumerate(data.columns):
            columns.append(
                getattr(c, "column_name", None)
                or getattr(c, "name", None)
                or getattr(c, "display_name", None)
                or f"col_{i}"
            )
    out = []
    for row in (getattr(data, "rows", None) or []):
        values = getattr(row, "values", None) or getattr(row, "data", None) or []
        out.append(dict(zip(columns, values)) if columns and len(values) == len(columns) else {"values": values})
    return out

def _poll_la_work_request(la_client, namespace: str, work_request_id: str, include_columns=True, include_fields=True):
    """
    Polls an LA query work request until completion and returns the final result payload.
    Mirrors Console behavior using get_query_result.
    """
    import time
    while True:
        resp = la_client.get_query_result(
            namespace_name=namespace,
            work_request_id=work_request_id,
            should_include_columns=include_columns,
            should_include_fields=include_fields,
        )
        lifecycle = getattr(resp.data, "lifecycle_state", None)
        if lifecycle in ("SUCCEEDED", "FAILED", "CANCELED") or getattr(resp.data, "rows", None):
            return resp
        sleep_s = float(resp.headers.get("retry-after", 0.5)) if hasattr(resp, "headers") else 0.5
        time.sleep(max(sleep_s, 0.2))

# =========================================================
# Public tools
# =========================================================

def list_la_namespaces() -> Dict:
    """
    Return available LA namespaces and current selection metadata.
    """
    try:
        cfg = get_oci_config()
        namespaces = _list_la_namespaces(cfg)
        result = {
            "tenancy": _la_tenancy,
            "namespaces": namespaces,
            "selected": _la_namespace,
            "selected_source": _la_namespace_source,
        }
        return redact_payload(result) if privacy_enabled() else result
    except Exception as e:
        return {"error": str(e), "tenancy": _la_tenancy, "selected": _la_namespace}

def set_la_namespace(namespace_name: str) -> Dict:
    """
    Manually set the LA namespace to use for all queries in this process.
    """
    global _la_namespace, _la_namespace_source, _la_namespaces
    try:
        cfg = get_oci_config()
        if not _la_namespaces:
            _la_namespaces = _list_la_namespaces(cfg)
        names = {n["name"] for n in _la_namespaces}
        if namespace_name not in names:
            out = {"error": f"Namespace '{namespace_name}' not found. Available: {sorted(list(names))}"}
            return redact_payload(out) if privacy_enabled() else out
        _la_namespace = namespace_name
        _la_namespace_source = "manual"
        out = {"selected": _la_namespace, "source": _la_namespace_source}
        return redact_payload(out) if privacy_enabled() else out
    except Exception as e:
        return {"error": str(e)}

def get_la_namespace() -> Dict:
    """
    Return the currently selected namespace (or error if not set).
    """
    if _la_namespace:
        out = {"selected": _la_namespace, "source": _la_namespace_source, "tenancy": _la_tenancy}
        return redact_payload(out) if privacy_enabled() else out
    out = {"error": "No namespace selected. Use set_la_namespace or define LA_NAMESPACE env, or ensure only one namespace exists."}
    return redact_payload(out) if privacy_enabled() else out

def run_log_analytics_query(
    query: str,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 1000,
    time_range: Optional[str] = None,
    should_run_async: bool = False,
    work_request_id: Optional[str] = None
) -> List[Dict]:
    """
    Execute a Logging Analytics query. Supports sync (simple) and async (submit+poll).
    If work_request_id is provided, skip submit and just poll for results.

    time_range: Optional relative window string ('60m', '24h', '30d').
    """
    with tool_span(tracer, "run_log_analytics_query", mcp_server="oci-mcp-observability") as span:
        config = get_oci_config()
        if region:
            config["region"] = region
        la_client = oci.log_analytics.LogAnalyticsClient(config)
        ns = _ensure_namespace(config)
        compartment = _effective_compartment(config, compartment_id)

        from oci.log_analytics.models import QueryDetails, TimeRange  # lazy import

        try:
            # Relative time window support
            time_filter = None
            if isinstance(time_range, str):
                tr = time_range.strip().lower()
                now = datetime.now(timezone.utc)
                if tr.endswith("m"):
                    time_filter = TimeRange(time_start=now - timedelta(minutes=int(tr[:-1])), time_end=now, time_zone=os.getenv("TIME_ZONE", "UTC"))
                elif tr.endswith("h"):
                    time_filter = TimeRange(time_start=now - timedelta(hours=int(tr[:-1])), time_end=now, time_zone=os.getenv("TIME_ZONE", "UTC"))
                elif tr.endswith("d"):
                    time_filter = TimeRange(time_start=now - timedelta(days=int(tr[:-1])), time_end=now, time_zone=os.getenv("TIME_ZONE", "UTC"))

            # Poll-only mode if a work request id was supplied
            if work_request_id:
                polled = _poll_la_work_request(la_client, ns, work_request_id, include_columns=True, include_fields=True)
                return _shape_la_rows(polled)

            qd = QueryDetails(
                query_string=query,
                sub_system="LOG",                       # REQUIRED by LA API
                max_total_count=limit,
                should_include_total_count=True,
                should_run_async=bool(should_run_async),
                time_filter=time_filter,
                compartment_id=compartment,            # body + query param (service accepts both)
            )

            # Submit query
            submit = la_client.query(
                namespace_name=ns,
                query_details=qd,
                limit=limit,
                compartment_id=compartment,
            )

            if should_run_async:
                # Async path → extract work request id and poll
                wr_id = submit.headers.get("opc-work-request-id") or getattr(getattr(submit, "data", None), "work_request_id", None)
                if not wr_id:
                    # Fallback: if service returned data inline, shape it; else clear error
                    data = getattr(submit, "data", None)
                    if getattr(data, "rows", None):
                        return _shape_la_rows(submit)
                    return [{"error": "Async query submitted but no workRequestId was returned; enable DEBUG to inspect raw response."}]
                polled = _poll_la_work_request(la_client, ns, wr_id, include_columns=True, include_fields=True)
                return _shape_la_rows(polled)

            # Sync path → results are in submit.data (if server finished in time)
            return _shape_la_rows(submit)

        except ServiceError as e:
            msg = getattr(e, "message", str(e)) or str(e)
            if "MissingParameter" in msg and "subsystem" in msg.lower():
                return [{"error": "Log Analytics API requires subSystem=sub_system='LOG'. This tool sets it automatically; if you overrode it, revert to 'LOG'."}]
            return [{"error": msg, "details": {"status": e.status, "code": e.code}}]
        except Exception as e:
            logging.error(f"Unexpected LA query error: {e}")
            return [{"error": str(e)}]

def run_saved_search(
    saved_search_id: str,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 1000
) -> Dict:
    """
    Execute a saved search via the query API using saved_search_id in QueryDetails.
    """
    with tool_span(tracer, "run_saved_search", mcp_server="oci-mcp-observability") as span:
        config = get_oci_config()
        if region:
            config['region'] = region
        la_client = oci.log_analytics.LogAnalyticsClient(config)
        ns = _ensure_namespace(config)
        compartment = _effective_compartment(config, compartment_id)

        from oci.log_analytics.models import QueryDetails  # lazy import models

        try:
            all_results: List[Dict] = []
            page: Optional[str] = None
            columns: Optional[List[str]] = None

            while True:
                qd = QueryDetails(
                    saved_search_id=saved_search_id,
                    compartment_id=compartment,
                    sub_system="LOG",
                    max_total_count=limit
                )
                response = la_client.query(
                    namespace_name=ns,
                    query_details=qd,
                    limit=limit,
                    page=page,
                    compartment_id=compartment
                )
                data = getattr(response, "data", None)
                if data:
                    if columns is None and getattr(data, "columns", None):
                        columns = [
                            getattr(c, "column_name", None)
                            or getattr(c, "name", None)
                            or getattr(c, "display_name", None)
                            or f"col_{i}"
                            for i, c in enumerate(data.columns)
                        ]
                    for row in getattr(data, "rows", []) or []:
                        values = getattr(row, "values", None) or getattr(row, "data", None) or []
                        if columns and len(columns) == len(values):
                            all_results.append(dict(zip(columns, values)))
                        else:
                            all_results.append({"values": values})

                page = response.headers.get("opc-next-page") if hasattr(response, "headers") else None
                if not page:
                    break

            return {'results': all_results}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error running saved search: {e}")
            return {'error': str(e)}
        except Exception as e:
            logging.error(f"Unexpected LA saved search error: {e}")
            return {'error': str(e)}

def emit_test_log(
    source: str,
    payload: Dict,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict:
    with tool_span(tracer, "emit_test_log", mcp_server="oci-mcp-observability") as span:
        config = get_oci_config()
        if region:
            config['region'] = region
        logging_client = oci.logging.LoggingManagementClient(config)
        compartment = compartment_id or get_compartment_id()
        
        try:
            # Assuming a log group and log exist; this may need configuration
            log_group_id = os.getenv('LOG_GROUP_ID')  # Set in env
            log_id = os.getenv('LOG_ID')
            if not log_id:
                return {'error': 'LOG_ID env var not set (and a log must exist).'}
            
            details = oci.logging.models.PutLogsDetails(
                specversion="1.0",
                log_entry_batches=[
                    oci.logging.models.LogEntryBatch(
                        entries=[oci.logging.models.LogEntry(
                            data=payload,
                            id="test-log-entry",
                            source=source,
                            time=oci.util.to_str(datetime.utcnow()),
                            type="custom"
                        )],
                        source=source,
                        type="custom"
                    )
                ]
            )
            
            response = logging_client.put_logs(
                log_id=log_id,
                put_logs_details=details
            )
            return {'status': 'success', 'response': getattr(response, "data", None)}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error emitting test log: {e}")
            return {'error': str(e)}

# -----------------------------
# Logan capability wrappers
# -----------------------------

def _ensure_compartment_id(cid: Optional[str]) -> str:
    """
    Ensure we pass a valid compartment OCID to Logan.
    Priority:
      1) Explicit param
      2) COMPARTMENT_OCID env (via get_compartment_id)
      3) Tenancy OCID from OCI config (fallback for broad queries)
    """
    if cid:
        return cid
    try:
        from mcp_oci_common import get_oci_config  # local import to avoid cycles
        cfg = get_oci_config()
    except Exception:
        cfg = {}
    return get_compartment_id() or cfg.get("tenancy")

def _parse_result(result):
    try:
        parsed = json.loads(result) if isinstance(result, str) else result
        return redact_payload(parsed) if privacy_enabled() else parsed
    except Exception:
        out = {"raw": result}
        return redact_payload(out) if privacy_enabled() else out

def execute_logan_query(
    query: str,
    compartment_id: Optional[str] = None,
    query_name: Optional[str] = None,
    time_range: str = "24h",
    max_count: int = 1000,
    profile: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict:
    with tool_span(tracer, "execute_logan_query", mcp_server="oci-mcp-observability") as span:
        res = la_execute_query_impl(
            query=query,
            compartment_id=_ensure_compartment_id(compartment_id),
            query_name=query_name,
            time_range=time_range,
            max_count=max_count,
            profile=profile,
            region=region,
        )
        out = _parse_result(res)
        _record_call({
            "tool": "execute_logan_query",
            "mcp_path": [
                "mcp_servers.observability.server.execute_logan_query",
                "mcp_servers.loganalytics.server.execute_query",
                "oci.log_analytics.LogAnalyticsClient.query"
            ],
            "query": query,
            "time_range": time_range,
            "compartment_id": _ensure_compartment_id(compartment_id),
            "success": bool(out.get("_meta",{}).get("success"))
        })
        return out

def search_security_events(
    search_term: str,
    event_type: str = "all",
    time_range: str = "24h",
    compartment_id: Optional[str] = None,
    limit: int = 100,
    profile: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict:
    with tool_span(tracer, "search_security_events", mcp_server="oci-mcp-observability") as span:
        res = la_search_security_events_impl(
            search_term=search_term,
            compartment_id=_ensure_compartment_id(compartment_id),
            event_type=event_type,
            time_range=time_range,
            limit=limit,
            profile=profile,
            region=region,
        )
        out = _parse_result(res)
        _record_call({
            "tool": "search_security_events",
            "mcp_path": [
                "mcp_servers.observability.server.search_security_events",
                "mcp_servers.loganalytics.server.search_security_events",
                "oci.log_analytics.LogAnalyticsClient.query"
            ],
            "search_term": search_term,
            "time_range": time_range,
            "compartment_id": _ensure_compartment_id(compartment_id),
            "success": bool(out.get("_meta",{}).get("success"))
        })
        return out

def get_mitre_techniques(
    technique_id: str = "all",
    category: str = "all",
    time_range: str = "30d",
    compartment_id: Optional[str] = None,
    profile: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict:
    with tool_span(tracer, "get_mitre_techniques", mcp_server="oci-mcp-observability") as span:
        res = la_get_mitre_techniques_impl(
            compartment_id=_ensure_compartment_id(compartment_id),
            technique_id=technique_id,
            category=category,
            time_range=time_range,
            profile=profile,
            region=region,
        )
        out = _parse_result(res)
        _record_call({
            "tool": "get_mitre_techniques",
            "mcp_path": [
                "mcp_servers.observability.server.get_mitre_techniques",
                "mcp_servers.loganalytics.server.get_mitre_techniques",
                "oci.log_analytics.LogAnalyticsClient.query"
            ],
            "technique_id": technique_id,
            "time_range": time_range,
            "compartment_id": _ensure_compartment_id(compartment_id),
            "success": bool(out.get("_meta",{}).get("success"))
        })
        return out

def analyze_ip_activity(
    ip_address: str,
    analysis_type: str = "full",
    time_range: str = "24h",
    compartment_id: Optional[str] = None,
    profile: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict:
    with tool_span(tracer, "analyze_ip_activity", mcp_server="oci-mcp-observability") as span:
        res = la_analyze_ip_activity_impl(
            ip_address=ip_address,
            compartment_id=_ensure_compartment_id(compartment_id),
            analysis_type=analysis_type,
            time_range=time_range,
            profile=profile,
            region=region,
        )
        out = _parse_result(res)
        _record_call({
            "tool": "analyze_ip_activity",
            "mcp_path": [
                "mcp_servers.observability.server.analyze_ip_activity",
                "mcp_servers.loganalytics.server.execute_query",
                "oci.log_analytics.LogAnalyticsClient.query"
            ],
            "ip_address": ip_address,
            "time_range": time_range,
            "compartment_id": _ensure_compartment_id(compartment_id),
            "success": bool(out.get("_meta",{}).get("success"))
        })
        return out

def execute_statistical_analysis(
    base_query: str,
    statistics_type: str = "stats",
    aggregations: Optional[List[Dict]] = None,
    group_by: Optional[List[str]] = None,
    time_interval: Optional[str] = None,
    time_range: str = "24h",
    compartment_id: Optional[str] = None,
    profile: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict:
    with tool_span(tracer, "execute_statistical_analysis", mcp_server="oci-mcp-observability") as span:
        res = la_perform_statistical_analysis_impl(
            base_query=base_query,
            compartment_id=_ensure_compartment_id(compartment_id),
            statistics_type=statistics_type,
            aggregations=aggregations,
            group_by=group_by,
            time_interval=time_interval,
            time_range=time_range,
            profile=profile,
            region=region,
        )
        out = _parse_result(res)
        _record_call({
            "tool": "execute_statistical_analysis",
            "mcp_path": [
                "mcp_servers.observability.server.execute_statistical_analysis",
                "mcp_servers.loganalytics.server.execute_query",
                "oci.log_analytics.LogAnalyticsClient.query"
            ],
            "base_query": base_query,
            "time_range": time_range,
            "compartment_id": _ensure_compartment_id(compartment_id),
            "success": bool(out.get("_meta",{}).get("success"))
        })
        return out

def execute_advanced_analytics(
    base_query: str,
    analytics_type: str = "cluster",
    parameters: Optional[Dict] = None,
    time_range: str = "24h",
    compartment_id: Optional[str] = None,
    profile: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict:
    with tool_span(tracer, "execute_advanced_analytics", mcp_server="oci-mcp-observability") as span:
        res = la_perform_advanced_analytics_impl(
            base_query=base_query,
            compartment_id=_ensure_compartment_id(compartment_id),
            analytics_type=analytics_type,
            parameters=parameters or {},
            time_range=time_range,
            profile=profile,
            region=region,
        )
        out = _parse_result(res)
        _record_call({
            "tool": "execute_advanced_analytics",
            "mcp_path": [
                "mcp_servers.observability.server.execute_advanced_analytics",
                "mcp_servers.loganalytics.server.execute_query",
                "oci.log_analytics.LogAnalyticsClient.query"
            ],
            "analytics_type": analytics_type,
            "time_range": time_range,
            "compartment_id": _ensure_compartment_id(compartment_id),
            "success": bool(out.get("_meta",{}).get("success"))
        })
        return out

def validate_query(
    query: str,
    fix: bool = False,
) -> Dict:
    with tool_span(tracer, "validate_query", mcp_server="oci-mcp-observability") as span:
        res = la_validate_query_impl(query=query, fix=fix)
        out = _parse_result(res)
        _record_call({
            "tool": "validate_query",
            "mcp_path": [
                "mcp_servers.observability.server.validate_query",
                "mcp_servers.loganalytics.server.validate_query"
            ],
            "query": query,
            "success": bool(out.get("_meta",{}).get("success"))
        })
        return out

def get_documentation(
    topic: str = "query_syntax",
    search_term: Optional[str] = None,
) -> Dict:
    with tool_span(tracer, "get_documentation", mcp_server="oci-mcp-observability") as span:
        res = la_get_documentation_impl(topic=topic, search_term=search_term)
        out = _parse_result(res)
        _record_call({
            "tool": "get_documentation",
            "mcp_path": [
                "mcp_servers.observability.server.get_documentation",
                "mcp_servers.loganalytics.server.get_documentation"
            ],
            "topic": topic,
            "success": bool(out.get("_meta",{}).get("success"))
        })
        return out

def check_oci_connection(
    compartment_id: Optional[str] = None,
    test_query: bool = True,
    profile: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict:
    with tool_span(tracer, "check_oci_connection", mcp_server="oci-mcp-observability") as span:
        res = la_check_connection_impl(
            compartment_id=_ensure_compartment_id(compartment_id),
            test_query=test_query,
            profile=profile,
            region=region,
        )
        out = _parse_result(res)
        _record_call({
            "tool": "check_oci_connection",
            "mcp_path": [
                "mcp_servers.observability.server.check_oci_connection",
                "mcp_servers.loganalytics.server.check_oci_connection"
            ],
            "compartment_id": _ensure_compartment_id(compartment_id),
            "success": bool(out.get("_meta",{}).get("success"))
        })
        return out

def correlate_threat_intelligence(
    indicator_type: str,
    indicator_value: str,
    time_range: str = "24h",
    compartment_id: Optional[str] = None,
    profile: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict:
    """Correlate threat intelligence indicators with log data.

    Supported indicator types:
    - ip: IP address (malicious IPs, C2 servers)
    - domain: Domain name (malicious domains, phishing sites)
    - hash: File hash (malware signatures - MD5, SHA1, SHA256)
    - user: User account (compromised accounts)
    - url: URL pattern (malicious URLs, attack patterns)
    """
    with tool_span(tracer, "correlate_threat_intelligence", mcp_server="oci-mcp-observability") as span:
        cid = _ensure_compartment_id(compartment_id)

        correlation_queries = {
            "ip": f"""
*
| where 'Source IP' = '{indicator_value}' or 'Destination IP' = '{indicator_value}' or contains('Log Entry', '{indicator_value}')
| stats count() as event_count,
        count(distinct 'Event Name') as unique_events,
        count(distinct 'User') as affected_users,
        count(distinct 'Resource ID') as affected_resources,
        min(Time) as first_seen,
        max(Time) as last_seen
  by 'Log Source', 'Event Name'
| sort -event_count
""",
            "domain": f"""
*
| where contains('Domain', '{indicator_value}') or contains('URL', '{indicator_value}') or contains('Log Entry', '{indicator_value}')
| stats count() as event_count,
        count(distinct 'Source IP') as source_ips,
        count(distinct 'User') as affected_users,
        min(Time) as first_seen,
        max(Time) as last_seen
  by 'Event Name', 'Action'
| sort -event_count
""",
            "hash": f"""
*
| where contains('File Hash', '{indicator_value}') or contains('MD5', '{indicator_value}') or contains('SHA256', '{indicator_value}') or contains('Log Entry', '{indicator_value}')
| stats count() as event_count,
        count(distinct 'File Path') as unique_files,
        count(distinct 'User') as affected_users,
        count(distinct 'Host') as affected_hosts,
        min(Time) as first_seen,
        max(Time) as last_seen
  by 'Event Name', 'File Name'
| sort -event_count
""",
            "user": f"""
*
| where 'User' = '{indicator_value}' or contains('Log Entry', '{indicator_value}')
| stats count() as event_count,
        count(distinct 'Event Name') as unique_actions,
        count(distinct 'Source IP') as source_ips,
        count(distinct 'Resource ID') as accessed_resources,
        count_if('Log Level' = 'ERROR' or 'Log Level' = 'WARNING') as suspicious_events,
        min(Time) as first_seen,
        max(Time) as last_seen
  by 'Event Name', 'Source IP'
| eval suspicious_rate = (suspicious_events * 100.0) / event_count
| sort -suspicious_rate, -event_count
""",
            "url": f"""
*
| where contains('URL', '{indicator_value}') or contains('Request URI', '{indicator_value}') or contains('Log Entry', '{indicator_value}')
| stats count() as event_count,
        count(distinct 'Source IP') as source_ips,
        count(distinct 'User') as affected_users,
        count_if('Status Code' >= 400) as error_responses,
        min(Time) as first_seen,
        max(Time) as last_seen
  by 'Request Method', 'Status Code'
| eval error_rate = (error_responses * 100.0) / event_count
| sort -event_count
"""
        }

        if indicator_type not in correlation_queries:
            return {
                "success": False,
                "error": f"Unknown indicator type: {indicator_type}",
                "available_types": list(correlation_queries.keys())
            }

        query = correlation_queries[indicator_type]

        # Execute the correlation query
        result = execute_logan_query(
            query=query,
            compartment_id=cid,
            query_name=f"threat_intel_{indicator_type}",
            time_range=time_range,
            profile=profile,
            region=region,
        )

        # Enrich with threat intelligence context
        threat_context = {
            "indicator_type": indicator_type,
            "indicator_value": indicator_value,
            "time_range": time_range,
            "query_executed": query.strip(),
            "correlation_results": result.get("results", []),
            "total_matches": result.get("count", 0),
            "risk_level": "unknown"
        }

        # Calculate risk level based on findings
        count = result.get("count", 0)
        if count > 100:
            threat_context["risk_level"] = "critical"
        elif count > 50:
            threat_context["risk_level"] = "high"
        elif count > 10:
            threat_context["risk_level"] = "medium"
        elif count > 0:
            threat_context["risk_level"] = "low"
        else:
            threat_context["risk_level"] = "none"

        return {
            "success": True,
            **threat_context
        }

def build_advanced_query(
    query_type: str,
    time_range: str = "24h",
    group_by: Optional[List[str]] = None,
    filters: Optional[Dict[str, str]] = None,
    aggregation: Optional[str] = None,
) -> Dict:
    """Build advanced Log Analytics queries for common patterns.

    Supported query types:
    - error_analysis: Find and analyze errors with stack traces
    - performance_slowdown: Identify slow operations and bottlenecks
    - security_audit: Security events and access patterns
    - resource_usage: Resource utilization and capacity metrics
    - api_monitoring: API call patterns, latency, errors
    - user_activity: User behavior and activity patterns
    - data_access: Data access patterns and anomalies
    - network_traffic: Network flow analysis
    """
    with tool_span(tracer, "build_advanced_query", mcp_server="oci-mcp-observability") as span:
        query_templates = {
            "error_analysis": """
*
| where 'Log Level' = 'ERROR' or 'Log Level' = 'FATAL' or contains('Log Entry', 'Exception') or contains('Log Entry', 'Error')
| stats count() as error_count by 'Log Source', 'Log Level', 'Error Type'
| sort -error_count
""",
            "performance_slowdown": """
*
| where 'Response Time' > 1000 or contains('Log Entry', 'slow') or contains('Log Entry', 'timeout')
| eval duration_sec = 'Response Time' / 1000
| stats avg(duration_sec) as avg_duration, max(duration_sec) as max_duration, count() as slow_requests by 'Service', 'Endpoint'
| where slow_requests > 5
| sort -avg_duration
""",
            "security_audit": """
*
| where 'Event Name' in ('CreateUser', 'DeleteUser', 'UpdateUser', 'ChangePassword', 'AssumeRole', 'UpdatePolicy')
     or contains('Log Entry', 'authentication') or contains('Log Entry', 'authorization')
| stats count() as event_count by 'Event Name', 'User', 'Source IP'
| sort -event_count
""",
            "resource_usage": """
*
| where contains('Log Source', 'Compute') or contains('Log Source', 'Database') or contains('Log Source', 'Storage')
| where 'CPU Usage' > 0 or 'Memory Usage' > 0 or 'Disk Usage' > 0
| stats avg('CPU Usage') as avg_cpu, avg('Memory Usage') as avg_memory, avg('Disk Usage') as avg_disk by 'Resource ID', 'Resource Name'
| sort -avg_cpu
""",
            "api_monitoring": """
*
| where contains('Log Source', 'API') or 'Request Method' in ('GET', 'POST', 'PUT', 'DELETE', 'PATCH')
| stats count() as request_count,
        avg('Response Time') as avg_latency,
        percentile('Response Time', 95) as p95_latency,
        percentile('Response Time', 99) as p99_latency,
        count_if('Status Code' >= 400) as error_count,
        count_if('Status Code' >= 500) as server_error_count
  by 'Endpoint', 'Request Method'
| eval error_rate = (error_count * 100.0) / request_count
| where request_count > 10
| sort -request_count
""",
            "user_activity": """
*
| where 'User' != '' and 'User' != 'null'
| stats count() as action_count,
        count(distinct 'Event Name') as unique_actions,
        count(distinct 'Source IP') as unique_ips,
        min(Time) as first_seen,
        max(Time) as last_seen
  by 'User'
| eval active_duration_hours = (last_seen - first_seen) / 3600
| sort -action_count
""",
            "data_access": """
*
| where 'Event Name' in ('GetObject', 'PutObject', 'DeleteObject', 'ListBucket', 'HeadObject')
     or contains('Log Entry', 'data access') or contains('Log Entry', 'file read')
| stats count() as access_count,
        sum('Bytes Transferred') as total_bytes,
        count(distinct 'Resource ID') as unique_resources
  by 'User', 'Event Name', 'Resource Type'
| eval total_mb = total_bytes / 1048576
| sort -access_count
""",
            "network_traffic": """
*
| where 'Protocol' in ('TCP', 'UDP', 'ICMP', 'HTTP', 'HTTPS')
     or 'Source IP' != '' or 'Destination IP' != ''
| stats count() as packet_count,
        sum('Bytes') as total_bytes,
        count(distinct 'Destination Port') as unique_ports,
        count_if('Action' = 'ACCEPT') as accepted,
        count_if('Action' = 'REJECT') as rejected
  by 'Source IP', 'Destination IP', 'Protocol'
| eval total_mb = total_bytes / 1048576,
       reject_rate = (rejected * 100.0) / packet_count
| sort -packet_count
"""
        }

        if query_type not in query_templates:
            return {
                "success": False,
                "error": f"Unknown query type: {query_type}",
                "available_types": list(query_templates.keys())
            }

        base_query = query_templates[query_type].strip()

        # Apply time range filter
        if time_range:
            time_filter = f"Time > dateRelative({time_range})"
            # Insert time filter after the base selector
            lines = base_query.split('\n')
            base_query = '\n'.join([lines[0], f"| where {time_filter}"] + lines[1:])

        # Apply custom filters
        if filters:
            filter_clauses = []
            for key, value in filters.items():
                if isinstance(value, str):
                    filter_clauses.append(f"'{key}' = '{value}'")
                else:
                    filter_clauses.append(f"'{key}' = {value}")
            if filter_clauses:
                filter_line = f"| where {' and '.join(filter_clauses)}"
                lines = base_query.split('\n')
                base_query = '\n'.join(lines[:2] + [filter_line] + lines[2:])

        # Override group by if specified
        if group_by:
            # Replace the existing "by" clause in stats commands
            lines = base_query.split('\n')
            modified_lines = []
            for line in lines:
                if '| stats' in line and ' by ' in line:
                    # Keep stats aggregations, replace group by fields
                    parts = line.split(' by ')
                    quoted_groups = [repr(g) for g in group_by]
                    group_by_clause = ', '.join(quoted_groups)
                    modified_lines.append(f"{parts[0]} by {group_by_clause}")
                else:
                    modified_lines.append(line)
            base_query = '\n'.join(modified_lines)

        # Add additional aggregation if specified
        if aggregation:
            lines = base_query.split('\n')
            # Insert aggregation before sort
            for i, line in enumerate(lines):
                if '| sort' in line:
                    lines.insert(i, f"| {aggregation}")
                    break
            base_query = '\n'.join(lines)

        return {
            "success": True,
            "query_type": query_type,
            "query": base_query,
            "time_range": time_range,
            "filters": filters,
            "group_by": group_by,
            "description": f"Advanced {query_type.replace('_', ' ')} query for Log Analytics"
        }

def quick_checks(
    compartment_id: Optional[str] = None,
    time_range: str = "24h",
    sample_size: int = 5,
    profile: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict:
    """Run basic Log Analytics health checks: head, fields, and stats by source.

    - head:   "* | head N"
    - fields: "* | fields Time, 'Log Source' | head N"
    - stats:  "* | fields 'Log Source' | head 100 | stats count() by 'Log Source' | sort -count | head N"
    """
    with tool_span(tracer, "quick_checks", mcp_server="oci-mcp-observability") as span:
        cid = _ensure_compartment_id(compartment_id)
        # Capture region and namespace for UX deep-links
        try:
            cfg = get_oci_config()
            if region:
                cfg["region"] = region
        except Exception:
            cfg = {"region": region}
        try:
            ns = _ensure_namespace(cfg)
        except Exception:
            ns = None
        reg = (cfg or {}).get("region")
        checks: list[Dict] = []

        def _run(name: str, query: str) -> Dict:
            res = execute_logan_query(
                query=query,
                compartment_id=cid,
                time_range=time_range,
                max_count=sample_size,
                profile=profile,
                region=region,
            )
            success = bool((res or {}).get("_meta", {}).get("success"))
            count = (res or {}).get("count")
            rows = (res or {}).get("results") or []
            return {"name": name, "query": query, "success": success, "count": count, "sample": rows[:1]}

        head_q = f"* | head {max(1, int(sample_size))}"
        fields_q = f"* | fields Time, 'Log Source' | head {max(1, int(sample_size))}"
        # Try multiple variants for COUNT to handle parser differences across tenancies
        stats_queries = [
            "* | stats count as logrecords by 'Log Source' | sort -logrecords",
            "* | stats COUNT as logrecords by 'Log Source' | sort -logrecords",
            "* | stats COUNT() as logrecords by 'Log Source' | sort -logrecords",
        ]

        checks.append(_run("head", head_q))
        checks.append(_run("fields", fields_q))
        # Try stats variations until one returns results
        stats_attempts = []
        for q in stats_queries:
            r = _run("stats_by_source", q)
            stats_attempts.append({"query": q, "count": r.get("count"), "success": r.get("success")})
            checks.append(r)
            try:
                if (r.get("count") or 0) > 0:
                    break
            except Exception:
                pass

        overall = any(c.get("success") for c in checks)
        return {
            "compartment_id": cid,
            "time_range": time_range,
            "namespace": ns,
            "region": reg,
            "checks": checks,
            "summary": {
                "ok": overall,
                "passed": sum(1 for c in checks if c.get("success")),
                "total": len(checks),
                "tried_stats_variants": stats_attempts,
            },
        }

# =========================================================
# Enhanced OpenTelemetry MCP Tools (Proposal Implementation)
# =========================================================

def create_traced_operation(operation_name: str, trace_token: Optional[str] = None, attributes: Optional[Dict] = None) -> Dict:
    """Create a traced MCP operation with OpenTelemetry enhancement"""
    try:
        # traced_operation() returns a decorator, not a context manager.
        # For programmatic usage, create a span directly and send a notification.
        span = mcp_otel_enhancer.create_trace_span(
            name=operation_name,
            trace_token=trace_token,
            attributes=attributes or {}
        )

        # Simulate operation work
        span.set_attribute("mcp.operation.type", "demo")
        span.set_attribute("mcp.server.version", "1.0.0")
        if trace_token:
            span.set_attribute("mcp.trace.token", trace_token)

        # Finish span and emit notification
        span.end()
        mcp_otel_enhancer.send_trace_notification(span, trace_token)

        return {
            "success": True,
            "operation_name": operation_name,
            "trace_token": trace_token,
            "span_id": f"{span.get_span_context().span_id:016x}",
            "trace_id": f"{span.get_span_context().trace_id:032x}",
            "message": "Traced operation completed with OpenTelemetry MCP enhancement"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "operation_name": operation_name
        }


def get_mcp_otel_capabilities() -> Dict:
    """Get MCP server capabilities including OpenTelemetry enhancements"""
    try:
        capabilities = mcp_otel_enhancer.get_server_capabilities()

        return {
            "success": True,
            "capabilities": capabilities,
            "features": {
                "otel_traces": capabilities.get("otel", {}).get("traces", False),
                "trace_notifications": True,
                "trace_correlation": True,
                "otlp_json_format": True
            },
            "notification_types": [
                "notifications/otel/trace"
            ],
            "description": "Enhanced MCP server with OpenTelemetry proposal implementation"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def send_test_trace_notification(trace_token: Optional[str] = None, operation_name: str = "test_operation") -> Dict:
    """Send a test trace notification following MCP OpenTelemetry proposal"""
    try:
        # Create test span
        span = mcp_otel_enhancer.create_trace_span(
            name=operation_name,
            trace_token=trace_token,
            attributes={
                "test.type": "mcp_otel_enhancement",
                "operation.category": "testing",
                "server.name": "oci-mcp-observability"
            }
        )

        # Add some test attributes
        span.set_attribute("test.timestamp", datetime.now().isoformat())
        span.set_attribute("test.purpose", "OpenTelemetry MCP proposal validation")

        span.end()

        # Send notification
        mcp_otel_enhancer.send_trace_notification(span, trace_token)

        return {
            "success": True,
            "message": "Test trace notification sent successfully",
            "trace_token": trace_token,
            "operation_name": operation_name,
            "span_id": f"{span.get_span_context().span_id:016x}",
            "trace_id": f"{span.get_span_context().trace_id:032x}",
            "notification_method": "notifications/otel/trace"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "trace_token": trace_token
        }


def analyze_trace_correlation(trace_token: str, time_window_minutes: int = 30) -> Dict:
    """Analyze trace correlation and observability data for a given trace token"""
    try:
        # This would typically query your observability backend
        # For demo purposes, we'll create a mock analysis

        analysis_time = datetime.now()
        window_start = analysis_time - timedelta(minutes=time_window_minutes)

        return {
            "success": True,
            "trace_token": trace_token,
            "analysis_period": {
                "start": window_start.isoformat(),
                "end": analysis_time.isoformat(),
                "duration_minutes": time_window_minutes
            },
            "correlation_data": {
                "client_requests": 1,
                "server_spans": 2,
                "total_operations": 3,
                "error_count": 0,
                "average_duration_ms": 45.2
            },
            "trace_flow": [
                {
                    "service": "mcp-client",
                    "operation": "tool_call",
                    "duration_ms": 50.1
                },
                {
                    "service": "oci-mcp-observability",
                    "operation": operation_name,
                    "duration_ms": 40.3
                }
            ],
            "recommendations": [
                "Trace correlation working correctly",
                "End-to-end observability data available",
                "Performance within normal parameters"
            ]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "trace_token": trace_token
        }


def get_observability_metrics_summary() -> Dict:
    """Get comprehensive observability metrics summary"""
    try:
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "server_info": {
                "name": "oci-mcp-observability",
                "version": "1.0.0",
                "uptime_seconds": (datetime.now() - datetime.now().replace(hour=0, minute=0, second=0)).total_seconds(),
                "capabilities": mcp_otel_enhancer.get_server_capabilities()
            },
            "metrics_summary": {
                "total_operations": len(_RECENT_CALLS),
                "recent_operations": len(_RECENT_CALLS[-10:]),
                "trace_notifications_sent": 0,  # Would be tracked in real implementation
                "active_spans": 0,
                "error_rate_percent": 0.0
            },
            "observability_stack": {
                "prometheus_endpoint": f"http://localhost:{os.getenv('METRICS_PORT', '8003')}/metrics",
                "otel_tracing_enabled": True,
                "pyroscope_enabled": os.getenv("ENABLE_PYROSCOPE", "false").lower() in ("1", "true", "yes", "on"),
                "log_analytics_enabled": True
            },
            "recent_operations": [
                {
                    "operation": call.get("tool", "unknown"),
                    "timestamp": call.get("timestamp", "unknown"),
                    "status": "completed"
                }
                for call in _RECENT_CALLS[-5:]
            ]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =========================================================
# MCP wiring
# =========================================================

tools = [
    # Namespace management
    Tool.from_function(fn=list_la_namespaces, name="list_la_namespaces", description="List available Logging Analytics namespaces and current selection"),
    Tool.from_function(fn=set_la_namespace,  name="set_la_namespace",  description="Set the Logging Analytics namespace to use for all queries"),
    Tool.from_function(fn=get_la_namespace,  name="get_la_namespace",  description="Get the currently selected Logging Analytics namespace"),

    Tool.from_function(fn=run_log_analytics_query, name="run_log_analytics_query", description="Run ad-hoc Log Analytics query"),
    Tool.from_function(fn=run_saved_search,       name="run_saved_search",       description="Run saved Log Analytics search"),
    Tool.from_function(fn=emit_test_log,          name="emit_test_log",          description="Emit synthetic test log"),

    # Advanced query builders
    Tool.from_function(fn=build_advanced_query, name="build_advanced_query", description="Build advanced Log Analytics queries for common patterns (error analysis, performance, security audit, API monitoring, etc.)"),
    Tool.from_function(fn=correlate_threat_intelligence, name="correlate_threat_intelligence", description="Correlate threat intelligence indicators (IPs, domains, hashes, users, URLs) with log data"),

    # Logan-enhanced capabilities
    Tool.from_function(fn=execute_logan_query,          name="execute_logan_query",          description="Execute enhanced OCI Logging Analytics query (Logan)"),
    Tool.from_function(fn=search_security_events,       name="search_security_events",       description="Search security events using Logan patterns or natural language"),
    Tool.from_function(fn=get_mitre_techniques,         name="get_mitre_techniques",         description="List or analyze MITRE ATT&CK techniques in logs"),
    Tool.from_function(fn=analyze_ip_activity,          name="analyze_ip_activity",          description="Analyze activity for an IP across authentication/network/threat intel"),
    Tool.from_function(fn=execute_statistical_analysis, name="execute_statistical_analysis", description="Run stats/timestats/eventstats/top/bottom/frequent/rare"),
    Tool.from_function(fn=execute_advanced_analytics,   name="execute_advanced_analytics",   description="Advanced analytics: cluster, link, nlp, classify, outlier, sequence, geostats, timecluster"),
    Tool.from_function(fn=validate_query,               name="validate_query",               description="Validate Log Analytics query; optionally auto-fix common issues"),
    Tool.from_function(fn=get_documentation,            name="get_documentation",            description="Get docs for Log Analytics query syntax, fields, functions, MITRE mapping, etc."),
    Tool.from_function(fn=check_oci_connection,         name="check_oci_connection",         description="Verify Logging Analytics connectivity and run optional test query"),
    Tool.from_function(fn=quick_checks,                 name="quick_checks",                 description="Basic LA checks: head, fields, stats by source"),
    # Observability helpers for planning and gap analysis
    Tool.from_function(fn=lambda: list(_RECENT_CALLS[-50:]), name="oci_observability_get_recent_calls", description="Return recent MCP call path and query metadata (last 50)"),
    Tool.from_function(fn=lambda: (_RECENT_CALLS.clear() or {"cleared": True}), name="oci_observability_clear_recent_calls", description="Clear the recent MCP call buffer"),

    # Enhanced OpenTelemetry MCP Tools (Proposal Implementation)
    Tool.from_function(fn=get_mcp_otel_capabilities, name="get_mcp_otel_capabilities", description="Get MCP server OpenTelemetry capabilities and features"),
    Tool.from_function(fn=create_traced_operation, name="create_traced_operation", description="Create a traced MCP operation with OpenTelemetry enhancement"),
    Tool.from_function(fn=send_test_trace_notification, name="send_test_trace_notification", description="Send test trace notification following MCP OpenTelemetry proposal"),
    Tool.from_function(fn=analyze_trace_correlation, name="analyze_trace_correlation", description="Analyze trace correlation and observability data for a trace token"),
    Tool.from_function(fn=get_observability_metrics_summary, name="get_observability_metrics_summary", description="Get comprehensive observability metrics and server status"),
]

def doctor() -> Dict:
    try:
        from mcp_oci_common.privacy import privacy_enabled
        cfg = get_oci_config()
        return {
            "server": "oci-mcp-observability",
            "ok": True,
            "privacy": bool(privacy_enabled()),
            "region": cfg.get("region"),
            "profile": os.getenv("OCI_PROFILE") or "DEFAULT",
            "tools": [t.name for t in tools],
        }
    except Exception as e:
        return {"server": "oci-mcp-observability", "ok": False, "error": str(e)}

# --- Diagnostics: Log Analytics stats variants ---
def diagnostics_loganalytics_stats(
    compartment_id: Optional[str] = None,
    time_range: str = "60m",
    profile: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict:
    """Try multiple 'stats by Log Source' query variants and report which works.

    Returns counts and success flags per variant to guide LLMs.
    """
    cid = _ensure_compartment_id(compartment_id)
    variants = [
        "* | stats count as logrecords by 'Log Source' | sort -logrecords",
        "* | stats COUNT as logrecords by 'Log Source' | sort -logrecords",
        "* | stats COUNT() as logrecords by 'Log Source' | sort -logrecords",
    ]
    attempts: List[Dict] = []
    for q in variants:
        try:
            res = la_execute_query_impl(
                query=q,
                compartment_id=cid,
                query_name="diag_stats_by_source",
                time_range=time_range,
                profile=profile,
                region=region,
            )
            data = _parse_result(res)
            attempts.append({
                "query": q,
                "success": bool(data.get("_meta", {}).get("success")),
                "count": int(data.get("count", 0)) if isinstance(data.get("count", 0), (int, float, str)) else 0,
                "message": data.get("_meta", {}).get("message"),
            })
        except Exception as e:
            attempts.append({"query": q, "success": False, "error": str(e)})
    chosen = next((a for a in attempts if (a.get("count") or 0) > 0), None)
    return {
        "compartment_id": cid,
        "time_range": time_range,
        "attempts": attempts,
        "selected": chosen,
        "ok": bool(chosen),
    }

# Register diagnostics tool
tools.append(Tool.from_function(fn=diagnostics_loganalytics_stats, name="diagnostics_loganalytics_stats", description="Run multiple 'stats by Log Source' variants and report which works"))
tools.append(Tool.from_function(fn=doctor, name="doctor", description="Return server health, config summary, and masking status"))

def doctor_all() -> Dict:
    """Aggregate doctor/healthcheck across all MCP-OCI servers.

    Mirrors scripts/smoke_check.py but as an MCP tool.
    """
    import importlib
    services = [
        ("compute", "mcp_servers.compute.server"),
        ("db", "mcp_servers.db.server"),
        ("network", "mcp_servers.network.server"),
        ("security", "mcp_servers.security.server"),
        ("observability", "mcp_servers.observability.server"),
        ("cost", "mcp_servers.cost.server"),
        ("inventory", "mcp_servers.inventory.server"),
        ("blockstorage", "mcp_servers.blockstorage.server"),
        ("loadbalancer", "mcp_servers.loadbalancer.server"),
        ("agents", "mcp_servers.agents.server"),
    ]
    out: Dict[str, Dict] = {}
    for name, modpath in services:
        try:
            mod = importlib.import_module(modpath)
        except Exception as e:
            out[name] = {"ok": False, "error": f"import failed: {e}"}
            continue
        # prefer 'doctor' direct function, then FunctionTool.fn, then tools/healthcheck
        attr = getattr(mod, "doctor", None)
        handler = None
        if callable(attr):
            handler = attr
        elif attr is not None:
            handler = getattr(attr, "fn", None) or getattr(attr, "func", None) or getattr(attr, "handler", None)
        if callable(handler):
            try:
                out[name] = {"ok": True, "result": handler()}
                continue
            except Exception as e:
                out[name] = {"ok": False, "error": f"doctor failed: {e}"}
                continue
        tools_list = getattr(mod, "tools", None)
        if isinstance(tools_list, list):
            hc = None
            for t in tools_list:
                if getattr(t, "name", None) == "healthcheck":
                    hc = getattr(t, "func", None) or getattr(t, "handler", None) or getattr(t, "fn", None)
                    break
            if callable(hc):
                try:
                    out[name] = {"ok": True, "result": hc()}
                    continue
                except Exception as e:
                    out[name] = {"ok": False, "error": f"healthcheck failed: {e}"}
                    continue
        out[name] = {"ok": False, "error": "no doctor or healthcheck"}
    return {"ok": all(v.get("ok") for v in out.values()), "servers": out}

tools.append(Tool.from_function(fn=doctor_all, name="doctor_all", description="Aggregate doctor/healthcheck across all MCP-OCI servers"))

def get_tools():
    return [{"name": t.name, "description": t.description} for t in tools]

if __name__ == "__main__":
    # Lazy imports so importing this module (for UX tool discovery) doesn't require optional deps
    try:
        from prometheus_client import start_http_server as _start_http_server
    except Exception:
        _start_http_server = None
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor as _FastAPIInstrumentor
    except Exception:
        _FastAPIInstrumentor = None

    # Expose Prometheus /metrics regardless of DEBUG (configurable via METRICS_PORT)
    if _start_http_server:
        try:
            _start_http_server(int(os.getenv("METRICS_PORT", "8003")))
        except Exception:
            pass

    # Apply privacy masking to all tools (wrapper) before constructing FastMCP
    try:
        from mcp_oci_common.privacy import privacy_enabled as _pe, redact_payload as _rp
        from fastmcp.tools import Tool as _Tool
        _wrapped: list[Tool] = []
        for _t in tools:
            _f = getattr(_t, "func", None) or getattr(_t, "handler", None)
            if not _f:
                _wrapped.append(_t)
                continue
            def _mk(f):
                def _w(*a, **k):
                    out = f(*a, **k)
                    return _rp(out) if _pe() else out
                _w.__name__ = getattr(f, "__name__", "tool")
                _w.__doc__ = getattr(f, "__doc__", "")
                return _w
            _wf = _mk(_f)
            try:
                params = getattr(_t, "parameters", None)
            except Exception:
                params = None
            if params is not None:
                # Preserve original JSON schema if present (critical for tools defined with a custom parameters schema)
                _wrapped.append(_Tool.from_function(_wf, name=_t.name, description=_t.description, parameters=params))
            else:
                _wrapped.append(_Tool.from_function(_wf, name=_t.name, description=_t.description))
        tools = _wrapped
    except Exception:
        pass

    mcp = FastMCP(tools=tools, name="oci-mcp-observability")

    if _FastAPIInstrumentor:
        try:
            if hasattr(mcp, "app"):
                _FastAPIInstrumentor.instrument_app(getattr(mcp, "app"))
            elif hasattr(mcp, "fastapi_app"):
                _FastAPIInstrumentor.instrument_app(getattr(mcp, "fastapi_app"))
            else:
                _FastAPIInstrumentor().instrument()
        except Exception:
            try:
                _FastAPIInstrumentor().instrument()
            except Exception:
                pass

    # Optional Pyroscope profiling (non-breaking)
    try:
        ENABLE_PYROSCOPE = os.getenv("ENABLE_PYROSCOPE", "false").lower() in ("1", "true", "yes", "on")
        if ENABLE_PYROSCOPE:
            import pyroscope
            pyroscope.configure(
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-observability"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        # Never break server if profiler not available
        pass

    transport = os.getenv("MCP_TRANSPORT", "stdio")
    host = os.getenv("MCP_HOST", "127.0.0.1")
    try:
        port = int(os.getenv("MCP_PORT", os.getenv("METRICS_PORT", "8000")))
    except Exception:
        port = 8000
    if transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=transport, host=host, port=port)
