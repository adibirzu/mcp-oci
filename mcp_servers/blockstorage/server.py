import os
import logging
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP
from fastmcp.tools import Tool
import oci
from opentelemetry import trace
from oci.pagination import list_call_get_all_results
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes

from mcp_oci_common import get_oci_config, get_compartment_id, allow_mutations, validate_and_log_tools
from mcp_oci_common.session import get_client

# Set up tracing with proper Resource
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-blockstorage")
init_tracing(service_name="oci-mcp-blockstorage")
init_metrics()
tracer = trace.get_tracer("oci-mcp-blockstorage")

# Logging setup
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)
logger = logging.getLogger(__name__)

def _safe_serialize(obj):
    """Safely serialize OCI SDK objects and other complex types"""
    if obj is None:
        return None

    # Handle OCI SDK objects
    if hasattr(obj, '__dict__'):
        try:
            # Try to convert OCI objects to dict
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif hasattr(obj, '_data') and hasattr(obj._data, '__dict__'):
                return obj._data.__dict__
            else:
                # Fallback to manual serialization of object attributes
                result = {}
                for key, value in obj.__dict__.items():
                    if not key.startswith('_'):
                        result[key] = _safe_serialize(value)
                return result
        except Exception as e:
            return {"serialization_error": str(e), "original_type": str(type(obj))}

    # Handle lists and tuples
    elif isinstance(obj, (list, tuple)):
        return [_safe_serialize(item) for item in obj]

    # Handle dictionaries
    elif isinstance(obj, dict):
        return {key: _safe_serialize(value) for key, value in obj.items()}

    # Handle primitive types
    elif isinstance(obj, (str, int, float, bool)):
        return obj

    # For unknown types, try to convert to string
    else:
        try:
            return str(obj)
        except Exception:
            return {"unknown_type": str(type(obj))}

def list_volumes(
    compartment_id: Optional[str] = None,
    availability_domain: Optional[str] = None
) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_volumes", mcp_server="oci-mcp-blockstorage") as span:
        config = get_oci_config()
        blockstorage_client = get_client(oci.core.BlockstorageClient, region=config.get("region"))
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
            span.set_attribute("volumes.count", len(volumes))
            return [_safe_serialize(vol) for vol in volumes]
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
        blockstorage_client = get_client(oci.core.BlockstorageClient, region=config.get("region"))

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
            return _safe_serialize(volume)
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error creating volume: {e}")
            span.record_exception(e)
            return {'error': str(e)}


tools = [
    Tool.from_function(
        fn=lambda: {"status": "ok", "server": "oci-mcp-blockstorage", "pid": os.getpid()},
        name="healthcheck",
        description="Lightweight readiness/liveness check for the block storage server"
    ),
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
    Tool.from_function(
        fn=lambda: (lambda _cfg=get_oci_config(): {
            "server": "oci-mcp-blockstorage",
            "ok": True,
            "region": _cfg.get("region"),
            "profile": os.getenv("OCI_PROFILE") or "DEFAULT",
            "tools": [t.name for t in tools]
        })(),
        name="doctor",
        description="Return server health, config summary, and masking status"
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
    # Validate MCP tool names at startup
    if not validate_and_log_tools(tools, "oci-mcp-blockstorage"):
        logging.error("MCP tool validation failed. Server will not start.")
        exit(1)

    # Apply privacy masking to all tools (wrapper)
    try:
        from mcp_oci_common.privacy import privacy_enabled as _pe, redact_payload as _rp
        from fastmcp.tools import Tool as _Tool
        _wrapped = []
        for _t in tools:
            _f = getattr(_t, "func", None) or getattr(_t, "handler", None)
            if not _f:
                _wrapped.append(_t)
                continue
            def _mk(f):
                def _w(*a, **k):
                    out = f(*a, **k)
                    return _rp(out) if _pe() else out
                _w.__name__ = getattr(f, "__name__", "tool")
                _w.__doc__ = getattr(f, "__doc__", "")
                return _w
            _wrapped.append(_Tool.from_function(_mk(_f), name=_t.name, description=_t.description))
        tools = _wrapped
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
