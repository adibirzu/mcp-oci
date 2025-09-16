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
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from prometheus_client import start_http_server

from mcp_oci_common import get_oci_config, get_compartment_id

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing
if not trace.get_tracer_provider():
    trace.set_tracer_provider(TracerProvider())
    otlp_exporter = OTLPSpanExporter(endpoint=os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317'), insecure=True)
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
tracer = trace.get_tracer(__name__)

def get_cost_summary(
    time_window: str = "7d",
    granularity: str = "DAILY",
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict:
    with tracer.start_as_current_span("get_cost_summary"):
        config = get_oci_config()
        if region:
            config['region'] = region
        usage_client = oci.usage_api.UsageapiClient(config)
        compartment = compartment_id or get_compartment_id()
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7) if time_window == "7d" else end_time - timedelta(days=30)
        
        try:
            response = usage_client.summarize_usage(
                compartment_id=compartment,
                time_usage_started=start_time,
                time_usage_ended=end_time,
                granularity=granularity.upper()
            )
            return {'total_cost': sum(item.computed_amount for item in response.data.items) if response.data.items else 0}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting cost summary: {e}")
            return {'error': str(e)}

def get_usage_breakdown(
    service: Optional[str] = None,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> List[Dict]:
    with tracer.start_as_current_span("get_usage_breakdown"):
        config = get_oci_config()
        if region:
            config['region'] = region
        usage_client = oci.usage_api.UsageapiClient(config)
        compartment = compartment_id or get_compartment_id()
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)
        
        filter_expr = f"service = '{service}'" if service else None
        
        try:
            response = usage_client.summarize_usage(
                compartment_id=compartment,
                time_usage_started=start_time,
                time_usage_ended=end_time,
                granularity="DAILY",
                group_by=["service"],
                filter=filter_expr
            )
            return [{'service': item.dimensions[0].value, 'usage': sum(dp.value for dp in item.aggregated_values)} 
                    for item in response.data.items if item.dimensions]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting usage breakdown: {e}")
            return [{'error': str(e)}]

def detect_cost_anomaly(
    series: List[float],
    method: str = "zscore",
    threshold: float = 3.0
) -> Dict:
    with tracer.start_as_current_span("detect_cost_anomaly"):
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

def detect_budget_drift(
    budget_amount: float,
    time_window: str = "7d",
    threshold_pct: float = 10.0,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict:
    with tracer.start_as_current_span("detect_budget_drift"):
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
        description="Get cost summary"
    ),
    Tool.from_function(
        fn=get_usage_breakdown,
        name="get_usage_breakdown",
        description="Get usage breakdown by service"
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
    )
]

if __name__ == "__main__":
    if os.getenv('DEBUG'):
        start_http_server(8004)  # Expose /metrics in debug mode
    mcp = FastMCP(tools=tools, name="oci-mcp-cost")
    mcp.run()
