import os
import logging
import oci
from typing import Dict, Optional, List
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

def run_log_analytics_query(
    query: str,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 1000
) -> List[Dict]:
    with tracer.start_as_current_span("run_log_analytics_query"):
        config = get_oci_config()
        if region:
            config['region'] = region
        log_analytics_client = oci.log_analytics.LogAnalyticsClient(config)
        compartment = compartment_id or get_compartment_id()
        
        try:
            response = log_analytics_client.query(
                namespace="default",  # Adjust if needed
                query=query,
                compartment_id=compartment,
                limit=limit
            )
            return response.data  # Assuming it returns list of dicts
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error running LA query: {e}")
            return [{'error': str(e)}]

def run_saved_search(
    saved_search_id: str,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict:
    with tracer.start_as_current_span("run_saved_search"):
        config = get_oci_config()
        if region:
            config['region'] = region
        log_analytics_client = oci.log_analytics.LogAnalyticsClient(config)
        compartment = compartment_id or get_compartment_id()
        
        try:
            response = log_analytics_client.query(
                namespace="default",
                saved_search_id=saved_search_id,
                compartment_id=compartment
            )
            return {'results': response.data}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error running saved search: {e}")
            return {'error': str(e)}

def emit_test_log(
    source: str,
    payload: Dict,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict:
    with tracer.start_as_current_span("emit_test_log"):
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

tools = [
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
]

if __name__ == "__main__":
    if os.getenv('DEBUG'):
        start_http_server(8003)  # Expose /metrics in debug mode
    mcp = FastMCP(tools=tools, name="oci-mcp-observability")
    mcp.run()
