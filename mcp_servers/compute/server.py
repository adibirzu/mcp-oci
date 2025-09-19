import os
import logging
import oci
from typing import List, Dict, Optional
from fastmcp import FastMCP
from fastmcp.tools import Tool
from datetime import datetime, timedelta
from opentelemetry import trace
from oci.pagination import list_call_get_all_results
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes
from mcp_oci_common.session import get_client

from mcp_oci_common import get_oci_config, get_compartment_id, allow_mutations
from mcp_oci_common.cache import get_cache

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing with proper Resource so service.name is set (avoids unknown_service)
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-compute")
init_tracing(service_name="oci-mcp-compute")
init_metrics()
tracer = trace.get_tracer("oci-mcp-compute")

def _fetch_instances(compartment_id: Optional[str] = None, region: Optional[str] = None, lifecycle_state: Optional[str] = None):
    """Internal function to fetch instances from OCI"""
    config = get_oci_config()
    if region:
        config['region'] = region
    compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
    compartment = compartment_id or get_compartment_id()

    # Normalize and validate lifecycle_state before calling OCI SDK
    lifecycle_state_param = None
    if lifecycle_state:
        # Handle empty strings or whitespace
        lifecycle_state = str(lifecycle_state).strip()
        if lifecycle_state:
            allowed_states = {"MOVING", "PROVISIONING", "RUNNING", "STARTING", "STOPPING", "STOPPED", "CREATING_IMAGE", "TERMINATING", "TERMINATED"}
            norm = lifecycle_state.upper()
            if norm not in allowed_states:
                raise ValueError(f"Invalid value for lifecycle_state. Allowed: {sorted(list(allowed_states))}")
            lifecycle_state_param = norm

    # Only pass lifecycle_state if it's not None
    kwargs = {'compartment_id': compartment}
    if lifecycle_state_param is not None:
        kwargs['lifecycle_state'] = lifecycle_state_param
    response = list_call_get_all_results(compute_client.list_instances, **kwargs)
    instances = response.data
    return [{
        'id': inst.id,
        'display_name': inst.display_name,
        'lifecycle_state': inst.lifecycle_state,
        'shape': inst.shape,
        'availability_domain': getattr(inst, 'availability_domain', ''),
        'compartment_id': getattr(inst, 'compartment_id', compartment),
        'time_created': getattr(inst, 'time_created', '').isoformat() if hasattr(inst, 'time_created') and inst.time_created else ''
    } for inst in instances]

def list_instances(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    lifecycle_state: Optional[str] = None,
    force_refresh: bool = False
) -> List[Dict]:
    with tool_span(tracer, "list_instances", mcp_server="oci-mcp-compute") as span:
        cache = get_cache()

        # Create params dict for caching
        params = {
            'compartment_id': compartment_id,
            'region': region,
            'lifecycle_state': lifecycle_state
        }

        try:
            # Get cached data or refresh
            instances = cache.get_or_refresh(
                server_name="oci-mcp-compute",
                operation="list_instances",
                params=params,
                fetch_func=lambda: _fetch_instances(compartment_id, region, lifecycle_state),
                force_refresh=force_refresh
            )

            span.set_attribute("instances.count", len(instances) if instances else 0)
            if compartment_id:
                span.set_attribute("compartment_id", compartment_id)
            if region:
                span.set_attribute("region", region)
            if lifecycle_state:
                span.set_attribute("lifecycle_state", lifecycle_state)

            return instances or []

        except ValueError as e:
            # Handle validation errors (like invalid lifecycle_state)
            return [{'error': str(e)}]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing instances: {e}")
            span.record_exception(e)
            return [{'error': str(e)}]

def start_instance(instance_id: str) -> Dict:
    with tool_span(tracer, "start_instance", mcp_server="oci-mcp-compute") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(compute_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Compute",
            oci_operation="InstanceAction(START)",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = compute_client.instance_action(instance_id, 'START')
            try:
                req_id = getattr(response, "headers", {}).get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error starting instance: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def stop_instance(instance_id: str) -> Dict:
    with tool_span(tracer, "stop_instance", mcp_server="oci-mcp-compute") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(compute_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Compute",
            oci_operation="InstanceAction(STOP)",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = compute_client.instance_action(instance_id, 'STOP')
            try:
                req_id = getattr(response, "headers", {}).get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error stopping instance: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def restart_instance(instance_id: str, hard: bool = False) -> Dict:
    with tool_span(tracer, "restart_instance", mcp_server="oci-mcp-compute") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(compute_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Compute",
            oci_operation="InstanceAction(RESET)",
            region=config.get("region"),
            endpoint=endpoint,
        )
        action = 'RESET' if hard else 'SOFTRESET'
        try:
            response = compute_client.instance_action(instance_id, action)
            try:
                req_id = getattr(response, "headers", {}).get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error restarting instance: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def create_instance(
    display_name: str,
    shape: str,
    subnet_id: str,
    source_type: str = "image",
    source_id: Optional[str] = None,
    compartment_id: Optional[str] = None,
    availability_domain: Optional[str] = None,
    ssh_public_keys: Optional[List[str]] = None
) -> Dict:
    with tool_span(tracer, "create_instance", mcp_server="oci-mcp-compute") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}

        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
        try:
            endpoint = getattr(compute_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Compute",
            oci_operation="LaunchInstance",
            region=config.get("region"),
            endpoint=endpoint,
        )

        # Create instance source details
        if source_type == "image":
            source_details = oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=source_id or "ocid1.image.oc1.eu-frankfurt-1.aaaaaaaav3v6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z"  # Default Ubuntu image
            )
        else:
            return {'error': f'Unsupported source_type: {source_type}. Use "image".'}

        # Create instance details
        create_instance_details = oci.core.models.LaunchInstanceDetails(
            compartment_id=compartment,
            display_name=display_name,
            shape=shape,
            source_details=source_details,
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=subnet_id
            )
        )

        if availability_domain:
            create_instance_details.availability_domain = availability_domain

        if ssh_public_keys:
            create_instance_details.metadata = {
                'ssh_authorized_keys': '\n'.join(ssh_public_keys)
            }

        try:
            response = compute_client.launch_instance(create_instance_details)
            req_id = getattr(response, "headers", {}).get("opc-request-id")
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            instance = response.data
            return {
                'id': instance.id,
                'display_name': instance.display_name,
                'lifecycle_state': instance.lifecycle_state,
                'shape': instance.shape,
                'availability_domain': getattr(instance, 'availability_domain', ''),
                'compartment_id': getattr(instance, 'compartment_id', compartment),
                'time_created': getattr(instance, 'time_created', '').isoformat() if hasattr(instance, 'time_created') and instance.time_created else ''
            }
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error creating instance: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def get_instance_metrics(instance_id: str, window: str = "1h") -> Dict:
    with tool_span(tracer, "get_instance_metrics", mcp_server="oci-mcp-compute") as span:
        config = get_oci_config()
        monitoring_client = get_client(oci.monitoring.MonitoringClient, region=config.get("region"))

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1) if window == "1h" else end_time - timedelta(days=1)

        query = f'CpuUtilization[1m]{{resourceId="{instance_id}"}}.mean()'
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(monitoring_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Monitoring",
            oci_operation="SummarizeMetricsData",
            region=config.get("region"),
            endpoint=endpoint,
        )
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
            try:
                req_id = getattr(response, "headers", {}).get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass

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
            span.record_exception(e)
            return {'error': str(e)}

def healthcheck() -> dict:
    return {"status": "ok", "server": "oci-mcp-compute", "pid": os.getpid()}

tools = [
    Tool.from_function(
        fn=healthcheck,
        name="healthcheck",
        description="Lightweight readiness/liveness check for the compute server"
    ),
    Tool.from_function(
        fn=list_instances,
        name="list_instances",
        description="List compute instances"
    ),
    Tool.from_function(
        fn=create_instance,
        name="create_instance",
        description="Create a new compute instance"
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
        fn=restart_instance,
        name="restart_instance",
        description="Restart a compute instance (soft by default, or hard reset if specified)"
    ),
    Tool.from_function(
        fn=get_instance_metrics,
        name="get_instance_metrics",
        description="Get CPU metrics summary for an instance"
    ),
]

# FastAPI instrumentation is imported lazily in __main__ to avoid hard dependency at import time

if __name__ == "__main__":
    # Lazy imports: avoid failing when optional deps are missing during module import
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
            _start_http_server(int(os.getenv("METRICS_PORT", "8001")))
        except Exception:
            pass
    mcp = FastMCP(tools=tools, name="oci-mcp-compute")
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
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-compute"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        # Never break server if profiler not available
        pass

    mcp.run()
