import os
import logging
import oci
from datetime import datetime, timedelta
from typing import List, Dict, Optional
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

def list_autonomous_databases(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> List[Dict]:
    with tracer.start_as_current_span("list_autonomous_databases"):
        config = get_oci_config()
        if region:
            config['region'] = region
        database_client = oci.database.DatabaseClient(config)
        compartment = compartment_id or get_compartment_id()
        
        try:
            dbs = database_client.list_autonomous_databases(compartment_id=compartment).data
            return [{
                'id': db.id,
                'display_name': db.display_name,
                'lifecycle_state': db.lifecycle_state,
                'db_workload': db.db_workload
            } for db in dbs]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing autonomous databases: {e}")
            return []

def list_db_systems(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> List[Dict]:
    with tracer.start_as_current_span("list_db_systems"):
        config = get_oci_config()
        if region:
            config['region'] = region
        database_client = oci.database.DatabaseClient(config)
        compartment = compartment_id or get_compartment_id()
        
        try:
            systems = database_client.list_db_systems(compartment_id=compartment).data
            return [{
                'id': sys.id,
                'display_name': sys.display_name,
                'lifecycle_state': sys.lifecycle_state,
                'shape': sys.shape
            } for sys in systems]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing DB systems: {e}")
            return []

def get_db_cpu_snapshot(db_id: str, window: str = "1h") -> Dict:
    with tracer.start_as_current_span("get_db_cpu_snapshot"):
        config = get_oci_config()
        monitoring_client = oci.monitoring.MonitoringClient(config)
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1) if window == "1h" else end_time - timedelta(days=1)
        
        query = f'CpuUtilization[1m]{{resourceId="{db_id}"}}.mean()'
        
        try:
            response = monitoring_client.summarize_metrics_data(
                compartment_id=get_compartment_id(),
                summarize_metrics_data_details=oci.monitoring.models.SummarizeMetricsDataDetails(
                    namespace="oci_database",
                    query=query,
                    start_time=start_time,
                    end_time=end_time
                )
            )
            if response.data:
                metrics = response.data[0].aggregated_datapoints
                summary = {
                    'average': sum(dp.value for dp in metrics) / len(metrics) if metrics else 0,
                    'max': max(dp.value for dp in metrics) if metrics else 0,
                    'min': min(dp.value for dp in metrics) if metrics else 0
                }
                return summary
            return {'error': 'No metrics found'}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting DB metrics: {e}")
            return {'error': str(e)}

tools = [
    Tool.from_function(
        fn=list_autonomous_databases,
        name="list_autonomous_databases",
        description="List autonomous databases"
    ),
    Tool.from_function(
        fn=list_db_systems,
        name="list_db_systems",
        description="List DB systems"
    ),
    Tool.from_function(
        fn=get_db_cpu_snapshot,
        name="get_db_cpu_snapshot",
        description="Get CPU metrics snapshot for a database"
    ),
]

if __name__ == "__main__":
    if os.getenv('DEBUG'):
        start_http_server(8002)  # Expose /metrics in debug mode
    mcp = FastMCP(tools=tools, name="oci-mcp-db")
    mcp.run()
