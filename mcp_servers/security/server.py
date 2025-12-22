import os
import logging
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP
from fastmcp.tools import Tool
import oci
from oci.identity import IdentityClient
from oci.cloud_guard import CloudGuardClient
from oci.data_safe import DataSafeClient
from mcp_oci_common import get_oci_config, get_compartment_id, add_oci_call_attributes, validate_and_log_tools, make_client
from mcp_oci_common.cache import get_cache
from mcp_oci_common.session import get_client
from mcp_oci_common.response import safe_serialize
from mcp_oci_common.otel import trace
from oci.pagination import list_call_get_all_results
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span
from mcp_oci_common.oci_apm import init_oci_apm_tracing
import json

# Load repo-local .env.local so OCI/OTEL config is applied consistently.
try:
    from pathlib import Path
    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(_repo_root / ".env.local")
except Exception:
    pass

# Set up tracing with proper Resource
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-security")
init_tracing(service_name="oci-mcp-security")
init_metrics()
# Initialize OCI APM tracing (uses OCI_APM_ENDPOINT and OCI_APM_PRIVATE_DATA_KEY)
init_oci_apm_tracing(service_name="oci-mcp-security")
tracer = trace.get_tracer("oci-mcp-security")

# Logging setup
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)
logger = logging.getLogger(__name__)


def _fetch_compartments(parent_compartment_id: Optional[str] = None):
    """Internal function to fetch compartments from OCI with full hierarchy support"""
    config = get_oci_config()
    identity_client = make_client(IdentityClient)

    # Always query from tenancy root to get full hierarchy
    # This ensures we get all compartments regardless of permissions
    tenancy_id = config.get("tenancy")

    # Use OCI API parameters for full compartment hierarchy
    kwargs = {
        'compartment_id': tenancy_id,
        'lifecycle_state': 'ACTIVE',
        'sort_by': 'NAME',
        'sort_order': 'ASC',
        'access_level': 'ANY',
        'compartment_id_in_subtree': True
    }

    logger.info(f"Querying compartments from tenancy root with kwargs: {kwargs}")
    logger.info(f"Tenancy ID: {tenancy_id}")

    response = list_call_get_all_results(identity_client.list_compartments, **kwargs)
    compartments = response.data
    logger.info(f"Found {len(compartments)} compartments from API")

    # Always include the root compartment since list_compartments doesn't include it
    try:
        root_compartment = identity_client.get_compartment(compartment_id=tenancy_id).data
        compartments.append(root_compartment)
        logger.info(f"Added root compartment: {root_compartment.name if hasattr(root_compartment, 'name') else 'N/A'}")
    except Exception as e:
        logger.warning(f"Could not fetch root compartment: {e}")

    logger.info(f"Total compartments after adding root: {len(compartments)}")

    return [{
        'id': comp.id,
        'name': comp.name,
        'description': getattr(comp, 'description', ''),
        'compartment_id': getattr(comp, 'compartment_id', ''),
        'lifecycle_state': getattr(comp, 'lifecycle_state', ''),
        'time_created': getattr(comp, 'time_created', '').isoformat() if hasattr(comp, 'time_created') and comp.time_created else ''
    } for comp in compartments]

def list_compartments(compartment_id: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_compartments", mcp_server="oci-mcp-security") as span:
        cache = get_cache()

        # Get cached data or refresh
        params = {'parent_compartment_id': compartment_id}
        all_compartments = cache.get_or_refresh(
            server_name="oci-mcp-security",
            operation="list_compartments",
            params=params,
            fetch_func=lambda: _fetch_compartments(compartment_id),
            force_refresh=force_refresh
        )

        if not all_compartments:
            return []

        span.set_attribute("compartments.total", len(all_compartments))
        if compartment_id:
            span.set_attribute("parent_compartment", compartment_id)
        return all_compartments

def list_iam_users(compartment_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_iam_users", mcp_server="oci-mcp-security") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        identity_client = make_client(oci.identity.IdentityClient)
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(identity_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Identity",
            oci_operation="ListUsers",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = list_call_get_all_results(identity_client.list_users, compartment_id=compartment)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            users = response.data
            span.set_attribute("users.count", len(users))
            return [{'name': user.name, 'id': user.id, 'description': getattr(user, 'description', '')} for user in users]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing IAM users: {e}")
            span.record_exception(e)
            return {'ok': False, 'error': str(e)}

def list_groups(compartment_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_groups", mcp_server="oci-mcp-security") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        identity_client = make_client(oci.identity.IdentityClient)
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(identity_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Identity",
            oci_operation="ListGroups",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = list_call_get_all_results(identity_client.list_groups, compartment_id=compartment)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            groups = response.data
            span.set_attribute("groups.count", len(groups))
            return [{'name': group.name, 'id': group.id, 'description': getattr(group, 'description', '')} for group in groups]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing groups: {e}")
            span.record_exception(e)
            return {'ok': False, 'error': str(e)}

def list_policies(compartment_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_policies", mcp_server="oci-mcp-security") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        identity_client = make_client(oci.identity.IdentityClient)
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(identity_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Identity",
            oci_operation="ListPolicies",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = list_call_get_all_results(identity_client.list_policies, compartment_id=compartment)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            policies = response.data
            span.set_attribute("policies.count", len(policies))
            return [{'name': policy.name, 'id': policy.id, 'description': getattr(policy, 'description', '')} for policy in policies]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing policies: {e}")
            span.record_exception(e)
            return {'ok': False, 'error': str(e)}

def list_cloud_guard_problems(compartment_id: Optional[str] = None, lifecycle_state: str = "OPEN", time_window: str = "24h") -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_cloud_guard_problems", mcp_server="oci-mcp-security") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        cloud_guard_client = make_client(CloudGuardClient)
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(cloud_guard_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="CloudGuard",
            oci_operation="ListProblems",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = list_call_get_all_results(cloud_guard_client.list_problems, compartment_id=compartment, lifecycle_state=lifecycle_state)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            problems = response.data
            data = [{'id': p.id, 'risk_level': p.risk_level, 'description': getattr(p, 'description', ''), 'lifecycle_state': getattr(p, 'lifecycle_state', lifecycle_state)} for p in problems]
            return {'ok': True, 'data': data}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing Cloud Guard problems: {e}")
            span.record_exception(e)
            return {'ok': False, 'error': str(e)}

def list_data_safe_findings(compartment_id: Optional[str] = None, profile: Optional[str] = None) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_data_safe_findings", mcp_server="oci-mcp-security") as span:
        # Stubbed in this build; Data Safe often not enabled in test envs
        return {'ok': False, 'error': 'NotImplemented: Data Safe integration requires tenancy enablement'}

# =============================================================================
# Server Manifest Resource
# =============================================================================

def server_manifest() -> str:
    """Server manifest resource for capability discovery."""
    manifest = {
        "name": "OCI MCP Security Server",
        "version": "1.0.0",
        "description": "OCI Security MCP Server for IAM, Cloud Guard, and Data Safe",
        "capabilities": {
            "skills": ["iam-management", "security-posture", "compliance-audit"],
            "tools": {
                "tier1_instant": ["healthcheck", "doctor"],
                "tier2_api": [
                    "list_compartments", "list_iam_users", "list_groups",
                    "list_policies", "list_cloud_guard_problems", "list_data_safe_findings"
                ],
                "tier3_heavy": [],
                "tier4_admin": []
            }
        },
        "usage_guide": "Use list_compartments for tenancy structure, list_iam_users/groups/policies for IAM audit, list_cloud_guard_problems for security issues.",
        "environment_variables": ["OCI_PROFILE", "OCI_REGION", "COMPARTMENT_OCID", "MCP_OCI_PRIVACY"]
    }
    return json.dumps(manifest, indent=2)

tools = [
    Tool.from_function(
        fn=lambda: {"status": "ok", "server": "oci-mcp-security", "pid": os.getpid()},
        name="healthcheck",
        description="Lightweight readiness/liveness check for the security server"
    ),
    Tool.from_function(
        fn=list_compartments,
        name="list_compartments",
        description="List all compartments in the tenancy"
    ),
    Tool.from_function(
        fn=list_iam_users,
        name="list_iam_users",
        description="List IAM users (read-only)"
    ),
    Tool.from_function(
        fn=list_groups,
        name="list_groups",
        description="List IAM groups (read-only)"
    ),
    Tool.from_function(
        fn=list_policies,
        name="list_policies",
        description="List IAM policies (read-only)"
    ),
    Tool.from_function(
        fn=list_cloud_guard_problems,
        name="list_cloud_guard_problems",
        description="List Cloud Guard problems"
    ),
    Tool.from_function(
        fn=list_data_safe_findings,
        name="list_data_safe_findings",
        description="List Data Safe findings (if enabled)"
    ),
    Tool.from_function(
        fn=lambda: (lambda _cfg=get_oci_config(): {
            "server": "oci-mcp-security",
            "ok": True,
            "region": _cfg.get("region"),
            "profile": os.getenv("OCI_PROFILE") or "DEFAULT",
            "tools": [t.name for t in tools]
        })(),
        name="doctor",
        description="Return server health, config summary, and masking status"
    ),
]

def get_tools():
    return [{"name": t.name, "description": t.description} for t in tools]

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
            _start_http_server(int(os.getenv("METRICS_PORT", "8004")))
        except Exception:
            pass

    # Validate MCP tool names at startup
    if not validate_and_log_tools(tools, "oci-mcp-security"):
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

    mcp = FastMCP(tools=tools, name="oci-mcp-security")

    # Register the server manifest resource
    @mcp.resource("server://manifest")
    def get_manifest() -> str:
        return server_manifest()

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
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-security"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        # Never break server if profiler not available
        pass

    mcp.run()


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
