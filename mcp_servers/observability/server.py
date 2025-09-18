import os
import logging
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span
# Tracing/metrics initialized below to ensure env (OTEL_SERVICE_NAME) is applied consistently
import oci
from typing import Dict, Optional, List
from fastmcp import FastMCP
from fastmcp.tools import Tool
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import json
import sys
from datetime import datetime

# Try to import enhanced Logan capabilities; if not found, add 'src' to sys.path and retry
try:
    from mcp_oci_loganalytics_enhanced.server import (
        execute_query as la_execute_query_impl,
        search_security_events as la_search_security_events_impl,
        get_mitre_techniques as la_get_mitre_techniques_impl,
        analyze_ip_activity as la_analyze_ip_activity_impl,
        perform_statistical_analysis as la_perform_statistical_analysis_impl,
        perform_advanced_analytics as la_perform_advanced_analytics_impl,
        validate_query as la_validate_query_impl,
        get_documentation as la_get_documentation_impl,
        check_connection as la_check_connection_impl,
    )
except Exception:
    _repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _src_path = os.path.join(_repo_root, "src")
    if _src_path not in sys.path:
        sys.path.insert(0, _src_path)
    # Ensure src/ versions of shared modules are used (avoid stale cache from root package)
    import sys as _sys
    _sys.modules.pop("mcp_oci_common", None)
    _sys.modules.pop("mcp_oci_common.responses", None)
    try:
        from mcp_oci_loganalytics_enhanced.server import (
            execute_query as la_execute_query_impl,
            search_security_events as la_search_security_events_impl,
            get_mitre_techniques as la_get_mitre_techniques_impl,
            analyze_ip_activity as la_analyze_ip_activity_impl,
            perform_statistical_analysis as la_perform_statistical_analysis_impl,
            perform_advanced_analytics as la_perform_advanced_analytics_impl,
            validate_query as la_validate_query_impl,
            get_documentation as la_get_documentation_impl,
            check_connection as la_check_connection_impl,
        )
    except Exception:
        # Defer to fallback stubs below
        pass

from mcp_oci_common import get_oci_config, get_compartment_id

# Fallback stubs if enhanced Logan module is unavailable
if "la_execute_query_impl" not in globals():
    def la_execute_query_impl(**kwargs):
        return {"success": False, "error": "Enhanced Log Analytics module not available"}
    def la_search_security_events_impl(**kwargs):
        return {"success": False, "error": "Enhanced Log Analytics module not available"}
    def la_get_mitre_techniques_impl(**kwargs):
        return {"success": False, "error": "Enhanced Log Analytics module not available"}
    def la_analyze_ip_activity_impl(**kwargs):
        return {"success": False, "error": "Enhanced Log Analytics module not available"}
    def la_perform_statistical_analysis_impl(**kwargs):
        return {"success": False, "error": "Enhanced Log Analytics module not available"}
    def la_perform_advanced_analytics_impl(**kwargs):
        return {"success": False, "error": "Enhanced Log Analytics module not available"}
    def la_validate_query_impl(**kwargs):
        return {"success": False, "error": "Enhanced Log Analytics module not available"}
    def la_get_documentation_impl(**kwargs):
        return {"success": False, "error": "Enhanced Log Analytics module not available"}
    def la_check_connection_impl(**kwargs):
        return {"success": False, "error": "Enhanced Log Analytics module not available"}

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing and metrics (consistent with other servers)
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-observability")
init_tracing(service_name="oci-mcp-observability")
init_metrics()
tracer = trace.get_tracer("oci-mcp-observability")

def run_log_analytics_query(
    query: str,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 1000
) -> List[Dict]:
    with tool_span(tracer, "run_log_analytics_query", mcp_server="oci-mcp-observability") as span:
        config = get_oci_config()
        if region:
            config['region'] = region
        log_analytics_client = oci.log_analytics.LogAnalyticsClient(config)
        compartment = compartment_id or get_compartment_id()
        
        try:
            all_results = []
            page = None
            columns = None
            while True:
                response = log_analytics_client.query(
                    namespace="default",
                    query=query,
                    compartment_id=compartment,
                    limit=limit,
                    page=page
                )
                if not columns and response.data.columns:
                    columns = [col.column_name for col in response.data.columns]
                if response.data.rows:
                    for row in response.data.rows:
                        if columns and len(columns) == len(row.values):
                            row_dict = dict(zip(columns, row.values))
                        else:
                            row_dict = {"values": row.values}
                        all_results.append(row_dict)
                page = response.headers.get("opc-next-page")
                if not page:
                    break
            return all_results
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error running LA query: {e}")
            return [{'error': str(e)}]

def run_saved_search(
    saved_search_id: str,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 1000
) -> Dict:
    with tool_span(tracer, "run_saved_search", mcp_server="oci-mcp-observability") as span:
        config = get_oci_config()
        if region:
            config['region'] = region
        log_analytics_client = oci.log_analytics.LogAnalyticsClient(config)
        compartment = compartment_id or get_compartment_id()
        
        try:
            all_results = []
            page = None
            columns = None
            while True:
                response = log_analytics_client.query(
                    namespace="default",
                    saved_search_id=saved_search_id,
                    compartment_id=compartment,
                    limit=limit,
                    page=page
                )
                if not columns and response.data.columns:
                    columns = [col.column_name for col in response.data.columns]
                if response.data.rows:
                    for row in response.data.rows:
                        if columns and len(columns) == len(row.values):
                            row_dict = dict(zip(columns, row.values))
                        else:
                            row_dict = {"values": row.values}
                        all_results.append(row_dict)
                page = response.headers.get("opc-next-page")
                if not page:
                    break
            return {'results': all_results}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error running saved search: {e}")
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
            return {'status': 'success', 'response': response.data}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error emitting test log: {e}")
            return {'error': str(e)}

# -----------------------------
# Logan capability wrappers
# -----------------------------

def _ensure_compartment_id(cid: Optional[str]) -> str:
    return cid or get_compartment_id()

def _parse_result(result):
    try:
        return json.loads(result) if isinstance(result, str) else result
    except Exception:
        return {"raw": result}

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
        return _parse_result(res)

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
        return _parse_result(res)

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
        return _parse_result(res)

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
        return _parse_result(res)

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
        return _parse_result(res)

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
        return _parse_result(res)

def validate_query(
    query: str,
    fix: bool = False,
) -> Dict:
    with tool_span(tracer, "validate_query", mcp_server="oci-mcp-observability") as span:
        res = la_validate_query_impl(query=query, fix=fix)
        return _parse_result(res)

def get_documentation(
    topic: str = "query_syntax",
    search_term: Optional[str] = None,
) -> Dict:
    with tool_span(tracer, "get_documentation", mcp_server="oci-mcp-observability") as span:
        res = la_get_documentation_impl(topic=topic, search_term=search_term)
        return _parse_result(res)

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
        return _parse_result(res)

tools = [
    # Legacy/basic observability tools
    Tool.from_function(
        fn=run_log_analytics_query,
        name="run_log_analytics_query",
        description="Run ad-hoc Log Analytics query"
    ),
    Tool.from_function(
        fn=run_saved_search,
        name="run_saved_search",
        description="Run saved Log Analytics search"
    ),
    Tool.from_function(
        fn=emit_test_log,
        name="emit_test_log",
        description="Emit synthetic test log"
    ),

    # Logan-enhanced capabilities
    Tool.from_function(
        fn=execute_logan_query,
        name="execute_logan_query",
        description="Execute enhanced OCI Logging Analytics query (Logan)"
    ),
    Tool.from_function(
        fn=search_security_events,
        name="search_security_events",
        description="Search security events using Logan patterns or natural language"
    ),
    Tool.from_function(
        fn=get_mitre_techniques,
        name="get_mitre_techniques",
        description="List or analyze MITRE ATT&CK techniques in logs"
    ),
    Tool.from_function(
        fn=analyze_ip_activity,
        name="analyze_ip_activity",
        description="Analyze activity for an IP across authentication/network/threat intel"
    ),
    Tool.from_function(
        fn=execute_statistical_analysis,
        name="execute_statistical_analysis",
        description="Run stats/timestats/eventstats/top/bottom/frequent/rare"
    ),
    Tool.from_function(
        fn=execute_advanced_analytics,
        name="execute_advanced_analytics",
        description="Advanced analytics: cluster, link, nlp, classify, outlier, sequence, geostats, timecluster"
    ),
    Tool.from_function(
        fn=validate_query,
        name="validate_query",
        description="Validate Log Analytics query; optionally auto-fix common issues"
    ),
    Tool.from_function(
        fn=get_documentation,
        name="get_documentation",
        description="Get docs for Log Analytics query syntax, fields, functions, MITRE mapping, etc."
    ),
    Tool.from_function(
        fn=check_oci_connection,
        name="check_oci_connection",
        description="Verify Logging Analytics connectivity and run optional test query"
    ),
]

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

    mcp.run()
