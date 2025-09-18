import os
import logging
from typing import Dict, Optional, List
from fastmcp import FastMCP
from fastmcp.tools import Tool
import oci
from opentelemetry import trace
from oci.pagination import list_call_get_all_results
from mcp_oci_common import get_oci_config, get_compartment_id, add_oci_call_attributes
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span

# Set up tracing with proper Resource
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-network")
init_tracing(service_name="oci-mcp-network")
init_metrics()
tracer = trace.get_tracer("oci-mcp-network")

# Logging setup
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)
logger = logging.getLogger(__name__)


def list_vcns(compartment_id: Optional[str] = None) -> List[Dict]:
    with tool_span(tracer, "list_vcns", mcp_server="oci-mcp-network") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        vn_client = oci.core.VirtualNetworkClient(config)
        try:
            endpoint = getattr(vn_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="VirtualNetwork",
            oci_operation="ListVcns",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = list_call_get_all_results(vn_client.list_vcns, compartment_id=compartment)
            req_id = response.headers.get("opc-request-id")
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            vcns = response.data
            return [{'display_name': vcn.display_name, 'id': vcn.id, 'cidr_block': getattr(vcn, 'cidr_block', '')} for vcn in vcns]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing VCNs: {e}")
            span.record_exception(e)
            return []

def list_subnets(vcn_id: str, compartment_id: Optional[str] = None) -> List[Dict]:
    with tool_span(tracer, "list_subnets", mcp_server="oci-mcp-network") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        vn_client = oci.core.VirtualNetworkClient(config)
        try:
            endpoint = getattr(vn_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="VirtualNetwork",
            oci_operation="ListSubnets",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = list_call_get_all_results(vn_client.list_subnets, compartment_id=compartment, vcn_id=vcn_id)
            req_id = response.headers.get("opc-request-id")
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            subnets = response.data
            return [{'display_name': subnet.display_name, 'id': subnet.id, 'cidr_block': subnet.cidr_block, 'vcn_id': vcn_id} for subnet in subnets]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing subnets: {e}")
            span.record_exception(e)
            return []

def create_vcn(
    display_name: str,
    cidr_block: str,
    compartment_id: Optional[str] = None,
    dns_label: Optional[str] = None
) -> Dict:
    with tool_span(tracer, "create_vcn", mcp_server="oci-mcp-network") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}

        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        vn_client = oci.core.VirtualNetworkClient(config)
        try:
            endpoint = getattr(vn_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="VirtualNetwork",
            oci_operation="CreateVcn",
            region=config.get("region"),
            endpoint=endpoint,
        )

        # Create VCN details
        create_vcn_details = oci.core.models.CreateVcnDetails(
            compartment_id=compartment,
            display_name=display_name,
            cidr_block=cidr_block
        )
        if dns_label:
            create_vcn_details.dns_label = dns_label

        try:
            response = vn_client.create_vcn(create_vcn_details)
            req_id = getattr(response, "headers", {}).get("opc-request-id")
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            vcn = response.data
            return {
                'id': vcn.id,
                'display_name': vcn.display_name,
                'cidr_block': getattr(vcn, 'cidr_block', ''),
                'dns_label': getattr(vcn, 'dns_label', ''),
                'lifecycle_state': getattr(vcn, 'lifecycle_state', ''),
                'time_created': getattr(vcn, 'time_created', '').isoformat() if hasattr(vcn, 'time_created') and vcn.time_created else ''
            }
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error creating VCN: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def create_subnet(
    vcn_id: str,
    display_name: str,
    cidr_block: str,
    availability_domain: Optional[str] = None,
    compartment_id: Optional[str] = None,
    dns_label: Optional[str] = None,
    prohibit_public_ip_on_vnic: bool = True
) -> Dict:
    with tool_span(tracer, "create_subnet", mcp_server="oci-mcp-network") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}

        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        vn_client = oci.core.VirtualNetworkClient(config)
        try:
            endpoint = getattr(vn_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="VirtualNetwork",
            oci_operation="CreateSubnet",
            region=config.get("region"),
            endpoint=endpoint,
        )

        # Create subnet details
        create_subnet_details = oci.core.models.CreateSubnetDetails(
            compartment_id=compartment,
            vcn_id=vcn_id,
            display_name=display_name,
            cidr_block=cidr_block,
            prohibit_public_ip_on_vnic=prohibit_public_ip_on_vnic
        )
        if availability_domain:
            create_subnet_details.availability_domain = availability_domain
        if dns_label:
            create_subnet_details.dns_label = dns_label

        try:
            response = vn_client.create_subnet(create_subnet_details)
            req_id = getattr(response, "headers", {}).get("opc-request-id")
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            subnet = response.data
            return {
                'id': subnet.id,
                'display_name': subnet.display_name,
                'vcn_id': subnet.vcn_id,
                'cidr_block': subnet.cidr_block,
                'availability_domain': getattr(subnet, 'availability_domain', ''),
                'dns_label': getattr(subnet, 'dns_label', ''),
                'prohibit_public_ip_on_vnic': getattr(subnet, 'prohibit_public_ip_on_vnic', True),
                'lifecycle_state': getattr(subnet, 'lifecycle_state', ''),
                'time_created': getattr(subnet, 'time_created', '').isoformat() if hasattr(subnet, 'time_created') and subnet.time_created else ''
            }
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error creating subnet: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def summarize_public_endpoints(compartment_id: Optional[str] = None) -> List[Dict]:
    with tool_span(tracer, "summarize_public_endpoints", mcp_server="oci-mcp-network") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        vn_client = oci.core.VirtualNetworkClient(config)
        try:
            endpoint = getattr(vn_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="VirtualNetwork",
            oci_operation="ListVcns",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = list_call_get_all_results(vn_client.list_vcns, compartment_id=compartment)
            req_id = response.headers.get("opc-request-id")
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            vcns = response.data
            public_endpoints = []
            for vcn in vcns:
                subnets_response = list_call_get_all_results(vn_client.list_subnets, compartment_id=compartment, vcn_id=vcn.id)
                subnets = subnets_response.data
                public_subnets = [s for s in subnets if not s.prohibit_public_ip_on_vnic]
                if public_subnets:
                    public_endpoints.append({
                        'vcn': vcn.display_name,
                        'vcn_id': vcn.id,
                        'public_subnets': len(public_subnets),
                        'total_subnets': len(subnets)
                    })
            return public_endpoints
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error summarizing public endpoints: {e}")
            span.record_exception(e)
            return []

tools = [
    Tool.from_function(
        fn=list_vcns,
        name="list_vcns",
        description="List VCNs in a compartment"
    ),
    Tool.from_function(
        fn=create_vcn,
        name="create_vcn",
        description="Create a new VCN (Virtual Cloud Network)"
    ),
    Tool.from_function(
        fn=list_subnets,
        name="list_subnets",
        description="List subnets in a VCN"
    ),
    Tool.from_function(
        fn=create_subnet,
        name="create_subnet",
        description="Create a new subnet in a VCN"
    ),
    Tool.from_function(
        fn=summarize_public_endpoints,
        name="summarize_public_endpoints",
        description="Summarize public endpoints in a compartment"
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
            _start_http_server(int(os.getenv("METRICS_PORT", "8006")))
        except Exception:
            pass
    mcp = FastMCP(tools=tools, name="oci-mcp-network")
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
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-network"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        # Never break server if profiler not available
        pass

    mcp.run()
