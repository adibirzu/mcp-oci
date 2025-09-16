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

from mcp_oci_common import get_oci_config, get_compartment_id, allow_mutations

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing
if not trace.get_tracer_provider():
    trace.set_tracer_provider(TracerProvider())
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)  # Adjust endpoint as needed
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
tracer = trace.get_tracer(__name__)

def list_instances(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    lifecycle_state: Optional[str] = None
) -> List[Dict]:
    with tracer.start_as_current_span("list_instances"):
        config = get_oci_config()
        if region:
            config['region'] = region
        compute_client = oci.core.ComputeClient(config)
        compartment = compartment_id or get_compartment_id()
        
        try:
            instances = compute_client.list_instances(compartment_id=compartment, lifecycle_state=lifecycle_state).data
            return [{
                'id': inst.id,
                'display_name': inst.display_name,
                'lifecycle_state': inst.lifecycle_state,
                'shape': inst.shape
            } for inst in instances]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing instances: {e}")
            return []

def start_instance(instance_id: str) -> Dict:
    with tracer.start_as_current_span("start_instance"):
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        compute_client = oci.core.ComputeClient(config)
        
        try:
            response = compute_client.instance_action(instance_id, 'START')
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error starting instance: {e}")
            return {'error': str(e)}

def stop_instance(instance_id: str) -> Dict:
    with tracer.start_as_current_span("stop_instance"):
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        compute_client = oci.core.ComputeClient(config)
        
        try:
            response = compute_client.instance_action(instance_id, 'STOP')
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error stopping instance: {e}")
            return {'error': str(e)}

def get_instance_metrics(instance_id: str, window: str = "1h") -> Dict:
    with tracer.start_as_current_span("get_instance_metrics"):
        config = get_oci_config()
        monitoring_client = oci.monitoring.MonitoringClient(config)
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1) if window == "1h" else end_time - timedelta(days=1)
        
        query = f'CpuUtilization[1m]{{resourceId="{instance_id}"}}.mean()'
        
        try:
            response = monitoring_client.summarize_metrics_data(
                compartment_id=get_compartment_id(),
                summarize_metrics_data_details=oci.monitoring.models.SummarizeMetricsDataDetails(
                    namespace="oci_computeagent",
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
            logging.error(f"Error getting metrics: {e}")
            return {'error': str(e)}

tools = [
    Tool.from_function(
        fn=list_instances,
        name="list_instances",
        description="List compute instances"
    ),
    Tool.from_function(
        fn=start_instance,
        name="start_instance",
        description="Start a compute instance"
    ),
    Tool.from_function(
        fn=stop_instance,
        name="stop_instance",
        description="Stop a compute instance"
    ),
    Tool.from_function(
        fn=get_instance_metrics,
        name="get_instance_metrics",
        description="Get CPU metrics summary for an instance"
    ),
]

if __name__ == "__main__":
    mcp = FastMCP(tools=tools, name="oci-mcp-compute")
    mcp.run()
