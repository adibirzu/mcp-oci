import os
import logging
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP
from fastmcp.tools import Tool
import oci
from opentelemetry import trace
from oci.pagination import list_call_get_all_results
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes

from mcp_oci_common import get_oci_config, get_compartment_id, allow_mutations

# Set up tracing with proper Resource
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-loadbalancer")
init_tracing(service_name="oci-mcp-loadbalancer")
init_metrics()
tracer = trace.get_tracer("oci-mcp-loadbalancer")

# Logging setup
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)
logger = logging.getLogger(__name__)


def list_load_balancers(compartment_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_load_balancers", mcp_server="oci-mcp-loadbalancer") as span:
        config = get_oci_config()
        load_balancer_client = oci.load_balancer.LoadBalancerClient(config)
        compartment = compartment_id or get_compartment_id()

        try:
            endpoint = getattr(load_balancer_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="LoadBalancer",
            oci_operation="ListLoadBalancers",
            region=config.get("region"),
            endpoint=endpoint,
        )

        try:
            response = list_call_get_all_results(load_balancer_client.list_load_balancers, compartment_id=compartment)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            load_balancers = response.data
            return [{
                'id': lb.id,
                'display_name': getattr(lb, 'display_name', ''),
                'lifecycle_state': getattr(lb, 'lifecycle_state', ''),
                'shape_name': getattr(lb, 'shape_name', ''),
                'shape_details': getattr(lb, 'shape_details', {}),
                'ip_addresses': getattr(lb, 'ip_addresses', []),
                'is_private': getattr(lb, 'is_private', False),
                'subnet_ids': getattr(lb, 'subnet_ids', []),
                'network_security_group_ids': getattr(lb, 'network_security_group_ids', []),
                'listeners': getattr(lb, 'listeners', {}),
                'backend_sets': getattr(lb, 'backend_sets', {}),
                'compartment_id': getattr(lb, 'compartment_id', compartment),
                'time_created': getattr(lb, 'time_created', '').isoformat() if hasattr(lb, 'time_created') and lb.time_created else ''
            } for lb in load_balancers]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing load balancers: {e}")
            span.record_exception(e)
            return []


def create_load_balancer(
    display_name: str,
    shape_name: str,
    compartment_id: Optional[str] = None,
    subnet_ids: Optional[List[str]] = None,
    is_private: bool = False,
    listeners: Optional[Dict[str, Any]] = None,
    backend_sets: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    with tool_span(tracer, "create_load_balancer", mcp_server="oci-mcp-loadbalancer") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}

        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        load_balancer_client = oci.load_balancer.LoadBalancerClient(config)

        try:
            endpoint = getattr(load_balancer_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="LoadBalancer",
            oci_operation="CreateLoadBalancer",
            region=config.get("region"),
            endpoint=endpoint,
        )

        # Create load balancer details
        create_lb_details = oci.load_balancer.models.CreateLoadBalancerDetails(
            compartment_id=compartment,
            display_name=display_name,
            shape_name=shape_name,
            is_private=is_private
        )

        if subnet_ids:
            create_lb_details.subnet_ids = subnet_ids

        if listeners:
            create_lb_details.listeners = listeners

        if backend_sets:
            create_lb_details.backend_sets = backend_sets

        try:
            response = load_balancer_client.create_load_balancer(create_lb_details)
            req_id = getattr(response, "headers", {}).get("opc-request-id")
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            lb = response.data
            return {
                'id': lb.id,
                'display_name': getattr(lb, 'display_name', ''),
                'lifecycle_state': getattr(lb, 'lifecycle_state', ''),
                'shape_name': getattr(lb, 'shape_name', ''),
                'shape_details': getattr(lb, 'shape_details', {}),
                'ip_addresses': getattr(lb, 'ip_addresses', []),
                'is_private': getattr(lb, 'is_private', False),
                'subnet_ids': getattr(lb, 'subnet_ids', []),
                'network_security_group_ids': getattr(lb, 'network_security_group_ids', []),
                'listeners': getattr(lb, 'listeners', {}),
                'backend_sets': getattr(lb, 'backend_sets', {}),
                'compartment_id': getattr(lb, 'compartment_id', compartment),
                'time_created': getattr(lb, 'time_created', '').isoformat() if hasattr(lb, 'time_created') and lb.time_created else ''
            }
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error creating load balancer: {e}")
            span.record_exception(e)
            return {'error': str(e)}


tools = [
    Tool.from_function(
        fn=list_load_balancers,
        name="list_load_balancers",
        description="List load balancers in a compartment"
    ),
    Tool.from_function(
        fn=create_load_balancer,
        name="create_load_balancer",
        description="Create a new load balancer"
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
            _start_http_server(int(os.getenv("METRICS_PORT", "8008")))
        except Exception:
            pass
    mcp = FastMCP(tools=tools, name="oci-mcp-loadbalancer")
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
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-loadbalancer"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        # Never break server if profiler not available
        pass

    mcp.run()
