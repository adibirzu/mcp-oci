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
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-blockstorage")
init_tracing(service_name="oci-mcp-blockstorage")
init_metrics()
tracer = trace.get_tracer("oci-mcp-blockstorage")

# Logging setup
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)
logger = logging.getLogger(__name__)


def list_volumes(
    compartment_id: Optional[str] = None,
    availability_domain: Optional[str] = None
) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_volumes", mcp_server="oci-mcp-blockstorage") as span:
        config = get_oci_config()
        blockstorage_client = oci.core.BlockstorageClient(config)
        compartment = compartment_id or get_compartment_id()

        try:
            endpoint = getattr(blockstorage_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Blockstorage",
            oci_operation="ListVolumes",
            region=config.get("region"),
            endpoint=endpoint,
        )

        try:
            kwargs = {'compartment_id': compartment}
            if availability_domain:
                kwargs['availability_domain'] = availability_domain

            response = list_call_get_all_results(blockstorage_client.list_volumes, **kwargs)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            volumes = response.data
            return [{
                'id': vol.id,
                'display_name': getattr(vol, 'display_name', ''),
                'size_in_gbs': getattr(vol, 'size_in_gbs', 0),
                'size_in_mbs': getattr(vol, 'size_in_mbs', 0),
                'lifecycle_state': getattr(vol, 'lifecycle_state', ''),
                'availability_domain': getattr(vol, 'availability_domain', ''),
                'compartment_id': getattr(vol, 'compartment_id', compartment),
                'time_created': getattr(vol, 'time_created', '').isoformat() if hasattr(vol, 'time_created') and vol.time_created else '',
                'vpus_per_gb': getattr(vol, 'vpus_per_gb', 0)
            } for vol in volumes]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing volumes: {e}")
            span.record_exception(e)
            return []


def create_volume(
    display_name: str,
    size_in_gbs: int,
    availability_domain: Optional[str] = None,
    compartment_id: Optional[str] = None,
    vpus_per_gb: Optional[int] = None
) -> Dict[str, Any]:
    with tool_span(tracer, "create_volume", mcp_server="oci-mcp-blockstorage") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}

        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        blockstorage_client = oci.core.BlockstorageClient(config)

        try:
            endpoint = getattr(blockstorage_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Blockstorage",
            oci_operation="CreateVolume",
            region=config.get("region"),
            endpoint=endpoint,
        )

        # Create volume details
        create_volume_details = oci.core.models.CreateVolumeDetails(
            compartment_id=compartment,
            display_name=display_name,
            size_in_gbs=size_in_gbs
        )

        if availability_domain:
            create_volume_details.availability_domain = availability_domain
        if vpus_per_gb:
            create_volume_details.vpus_per_gb = vpus_per_gb

        try:
            response = blockstorage_client.create_volume(create_volume_details)
            req_id = getattr(response, "headers", {}).get("opc-request-id")
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            volume = response.data
            return {
                'id': volume.id,
                'display_name': getattr(volume, 'display_name', ''),
                'size_in_gbs': getattr(volume, 'size_in_gbs', 0),
                'size_in_mbs': getattr(volume, 'size_in_mbs', 0),
                'lifecycle_state': getattr(volume, 'lifecycle_state', ''),
                'availability_domain': getattr(volume, 'availability_domain', ''),
                'compartment_id': getattr(volume, 'compartment_id', compartment),
                'time_created': getattr(volume, 'time_created', '').isoformat() if hasattr(volume, 'time_created') and volume.time_created else '',
                'vpus_per_gb': getattr(volume, 'vpus_per_gb', 0)
            }
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error creating volume: {e}")
            span.record_exception(e)
            return {'error': str(e)}


tools = [
    Tool.from_function(
        fn=list_volumes,
        name="list_volumes",
        description="List block storage volumes"
    ),
    Tool.from_function(
        fn=create_volume,
        name="create_volume",
        description="Create a new block storage volume"
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
            _start_http_server(int(os.getenv("METRICS_PORT", "8007")))
        except Exception:
            pass
    mcp = FastMCP(tools=tools, name="oci-mcp-blockstorage")
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
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-blockstorage"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        # Never break server if profiler not available
        pass

    mcp.run()
