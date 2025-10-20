import os
import logging
import oci
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import numpy as np
import pandas as pd
from scipy import stats
from fastmcp import FastMCP
from fastmcp.tools import Tool
from opentelemetry import trace

from mcp_oci_common import get_oci_config, get_compartment_id
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing with proper Resource
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-cost")
init_tracing(service_name="oci-mcp-cost")
init_metrics()
tracer = trace.get_tracer("oci-mcp-cost")

def get_cost_summary(
    time_window: str = "7d",
    granularity: str = "DAILY",
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict:
    with tool_span(tracer, "get_cost_summary", mcp_server="oci-mcp-cost") as span:
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
    with tool_span(tracer, "get_usage_breakdown", mcp_server="oci-mcp-cost") as span:
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
        
        filter_expr = f"service = '{service}'" if service else None
        
        try:
            details = oci.usage_api.models.RequestSummarizedUsagesDetails(
                tenant_id=config.get("tenancy"),
                time_usage_started=start_time.replace(hour=0, minute=0, second=0, microsecond=0),
                time_usage_ended=end_time.replace(hour=0, minute=0, second=0, microsecond=0),
                granularity="DAILY",
                query_type="COST",
                group_by=["service"]
            )
            response = usage_client.request_summarized_usages(
                request_summarized_usages_details=details
            )
            req_id = getattr(response, "headers", {}).get("opc-request-id") if hasattr(response, "headers") else None
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            items = getattr(getattr(response, "data", None), "items", None) or []

            # Aggregate by service and extract currency information
            agg = {}
            currency = "USD"  # Default fallback
            for item in items:
                svc = getattr(item, "service", None) or "UNKNOWN"
                if filter_expr and service and svc != service:
                    continue
                amt = getattr(item, "computed_amount", 0) or 0

                # Extract currency from the first item that has it
                if hasattr(item, "currency") and getattr(item, "currency"):
                    currency = str(getattr(item, "currency")).strip()

                if svc not in agg:
                    agg[svc] = {'usage': 0, 'currency': currency}
                agg[svc]['usage'] += amt

            # Convert to list format with currency information
            result = []
            for svc, data in sorted(agg.items()):
                result.append({
                    'service': svc,
                    'usage': data['usage'],
                    'currency': data['currency']
                })

            return result
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting usage breakdown: {e}")
            span.record_exception(e)
            return [{'error': str(e)}]

def detect_cost_anomaly(
    series: List[float],
    method: str = "zscore",
    threshold: float = 3.0
) -> Dict:
    with tool_span(tracer, "detect_cost_anomaly", mcp_server="oci-mcp-cost") as span:
        if not series:
            return {'anomalies': []}
        
        anomalies = []
        arr = np.array(series)
        
        if method == "zscore":
            z_scores = np.abs(stats.zscore(arr))
            anomalies = np.where(z_scores > threshold)[0].tolist()
        elif method == "ewm":
            ewm_mean = np.array(pd.Series(arr).ewm(span=5).mean())
            ewm_std = np.array(pd.Series(arr).ewm(span=5).std())
            anomalies = np.where(np.abs(arr - ewm_mean) > threshold * ewm_std)[0].tolist()
        
        return {'anomalies': anomalies, 'method': method, 'threshold': threshold}

def get_cost_timeseries(
    time_window: str = "30d",
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict:
    """Return daily cost time series for the given window using Usage API."""
    with tool_span(tracer, "get_cost_timeseries", mcp_server="oci-mcp-cost") as span:
        config = get_oci_config()
        if region:
            config['region'] = region
        usage_client = oci.usage_api.UsageapiClient(config)
        compartment = compartment_id or get_compartment_id()

        end_time = datetime.utcnow()
        days = 30
        if time_window.endswith('d'):
            try:
                days = int(time_window[:-1])
            except Exception:
                days = 30
        start_time = end_time - timedelta(days=days)

        try:
            details = oci.usage_api.models.RequestSummarizedUsagesDetails(
                tenant_id=config.get("tenancy"),
                time_usage_started=start_time.replace(hour=0, minute=0, second=0, microsecond=0),
                time_usage_ended=end_time.replace(hour=0, minute=0, second=0, microsecond=0),
                granularity="DAILY",
                query_type="COST"
            )
            response = usage_client.request_summarized_usages(
                request_summarized_usages_details=details
            )
            items = getattr(getattr(response, "data", None), "items", None) or []
            series = []
            for item in items:
                ts = getattr(item, 'time_usage_started', None) or getattr(item, 'time_usage_ended', None)
                amt = getattr(item, 'computed_amount', 0) or 0
                if ts:
                    # normalize to iso date
                    try:
                        iso = ts.strftime('%Y-%m-%d')
                    except Exception:
                        iso = str(ts)
                    series.append({"date": iso, "amount": amt})
            series.sort(key=lambda x: x['date'])
            return {"series": series, "window": time_window}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error requesting time series: {e}")
            span.record_exception(e)
            return {"error": str(e)}

def run_showusage(
    profile: Optional[str] = None,
    time_range: Optional[str] = None,
    granularity: str = "DAILY",
    service_filters: Optional[List[str]] = None,
    compartment_id: Optional[str] = None,
    output_format: str = "text",
    diff_mode: bool = True,
    limit: Optional[int] = None
) -> Dict:
    with tool_span(tracer, "run_showusage", mcp_server="oci-mcp-cost") as span:
        # Local imports for this tool (avoid global optional deps)
        import subprocess
        import json
        import hashlib
        import difflib
        import sys
        import shutil
        import os as _os
        from mcp_oci_common.observability import record_token_usage
        config_path = os.path.expanduser("~/.oci/config")
        # Choose a portable Python executable
        python_path = sys.executable or shutil.which("python3") or shutil.which("python") or "python"
        # Try to locate the showusage script relative to this file → repo root
        script_path = _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
            "third_party", "oci-python-sdk", "examples", "showusage", "showusage.py"
        )
        if not _os.path.exists(script_path):
            # Fallback relative to repo root if execution path differs
            script_path = _os.path.join(_os.getcwd(), "third_party", "oci-python-sdk", "examples", "showusage", "showusage.py")
        cmd = [python_path, script_path]
        
        if profile:
            cmd.extend(["--config-file", config_path, "--profile", profile])
        if time_range:
            # Parse time_range like "30d" to get days
            if time_range.endswith('d'):
                days = time_range[:-1]
                cmd.extend(["-ds", (datetime.utcnow() - timedelta(days=int(days))).strftime('%Y-%m-%d')])
                cmd.extend(["-ld", days])
        if granularity and granularity.upper() != "DAILY":
            cmd.extend(["-g", granularity.upper()])
        if service_filters:
            cmd.extend(["--service-filter", ",".join(service_filters)])
        if compartment_id:
            cmd.extend(["--compartment-id", compartment_id])
        
        param_str = json.dumps({
            "profile": profile,
            "time_range": time_range,
            "granularity": granularity,
            "service_filters": service_filters,
            "compartment_id": compartment_id,
            "output_format": output_format
        }, sort_keys=True)
        cache_key = hashlib.sha256(param_str.encode()).hexdigest()
        cache_dir = "/tmp/mcp-oci-cache/cost"
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{cache_key}.txt")
        prev_cache_file = os.path.join(cache_dir, f"{cache_key}.prev.txt")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                return {"error": result.stderr}
            
            output = result.stdout
            if limit:
                output = "\n".join(output.splitlines()[:limit])
            
            if os.path.exists(cache_file):
                os.rename(cache_file, prev_cache_file)
            with open(cache_file, "w") as f:
                f.write(output)
            
            if diff_mode and os.path.exists(prev_cache_file):
                with open(prev_cache_file, "r") as f:
                    prev_output = f.read()
                diff = list(difflib.unified_diff(
                    prev_output.splitlines(keepends=True),
                    output.splitlines(keepends=True),
                    fromfile="previous",
                    tofile="current"
                ))
                diff_text = "".join(diff)
                try:
                    record_token_usage(int(len(diff_text) / 4), attrs={"source": "showusage", "diff": True})
                except Exception:
                    pass
                return {"diff": diff_text, "changes_detected": bool(diff)}
            else:
                try:
                    record_token_usage(int(len(output) / 4), attrs={"source": "showusage", "diff": False})
                except Exception:
                    pass
                return {"output": output}
        
        except Exception as e:
            logging.error(f"Error running showusage: {e}")
            span.record_exception(e)
            return {"error": str(e)}

def detect_budget_drift(
    budget_amount: float,
    time_window: str = "7d",
    threshold_pct: float = 10.0,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict:
    with tool_span(tracer, "detect_budget_drift", mcp_server="oci-mcp-cost") as span:
        summary = get_cost_summary(time_window, "DAILY", compartment_id, region)
        if 'error' in summary:
            return summary

        days = 7 if time_window == "7d" else 30
        daily_run_rate = summary['total_cost'] / days
        projected_monthly = daily_run_rate * 30

        drift_pct = ((projected_monthly - budget_amount) / budget_amount) * 100 if budget_amount > 0 else 0

        return {
            'projected_monthly': projected_monthly,
            'drift_pct': drift_pct,
            'exceeds_threshold': abs(drift_pct) > threshold_pct,
            'threshold_pct': threshold_pct
        }

tools = [
    Tool.from_function(
        fn=get_cost_summary,
        name="get_cost_summary",
        description="Get cost summary with currency information for a specified time window"
    ),
    Tool.from_function(
        fn=get_usage_breakdown,
        name="get_usage_breakdown",
        description="Get usage breakdown by service with currency information"
    ),
    Tool.from_function(
        fn=detect_cost_anomaly,
        name="detect_cost_anomaly",
        description="Detect anomalies in cost series"
    ),
    Tool.from_function(
        fn=detect_budget_drift,
        name="detect_budget_drift",
        description="Detect budget drift based on run rate"
    ),
    Tool.from_function(
        fn=run_showusage,
        name="run_showusage",
        description="Run ShowUsage report with optional diff for changes"
    )
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
            _start_http_server(int(os.getenv("METRICS_PORT", "8005")))
        except Exception:
            pass
    mcp = FastMCP(tools=tools, name="oci-mcp-cost")
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
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-cost"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        # Never break server if profiler not available
        pass

    mcp.run()
