import os
import logging
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP
from fastmcp.tools import Tool
import oci
from oci.identity import IdentityClient
from oci.cloud_guard import CloudGuardClient
from oci.data_safe import DataSafeClient
from mcp_oci_common import get_oci_config, get_compartment_id, add_oci_call_attributes
from opentelemetry import trace
from oci.pagination import list_call_get_all_results
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span

# Set up tracing with proper Resource
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-security")
init_tracing(service_name="oci-mcp-security")
init_metrics()
tracer = trace.get_tracer("oci-mcp-security")

# Logging setup
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)
logger = logging.getLogger(__name__)


def list_compartments() -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_compartments", mcp_server="oci-mcp-security") as span:
        config = get_oci_config()
        identity_client = IdentityClient(config)

        # Enrich span with backend call metadata
        try:
            endpoint = getattr(identity_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Identity",
            oci_operation="ListCompartments",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = list_call_get_all_results(identity_client.list_compartments, compartment_id=config.get("tenancy"))
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            compartments = response.data
            return [{
                'id': comp.id,
                'name': comp.name,
                'description': getattr(comp, 'description', ''),
                'compartment_id': getattr(comp, 'compartment_id', ''),
                'lifecycle_state': getattr(comp, 'lifecycle_state', ''),
                'time_created': getattr(comp, 'time_created', '').isoformat() if hasattr(comp, 'time_created') and comp.time_created else ''
            } for comp in compartments]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing compartments: {e}")
            span.record_exception(e)
            return []

def list_iam_users(compartment_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_iam_users", mcp_server="oci-mcp-security") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        identity_client = IdentityClient(config)
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
            return [{'name': user.name, 'id': user.id, 'description': getattr(user, 'description', '')} for user in users]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing IAM users: {e}")
            span.record_exception(e)
            return []

def list_groups(compartment_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_groups", mcp_server="oci-mcp-security") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        identity_client = IdentityClient(config)
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
            return [{'name': group.name, 'id': group.id, 'description': getattr(group, 'description', '')} for group in groups]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing groups: {e}")
            span.record_exception(e)
            return []

def list_policies(compartment_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_policies", mcp_server="oci-mcp-security") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        identity_client = IdentityClient(config)
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
            return [{'name': policy.name, 'id': policy.id, 'description': getattr(policy, 'description', '')} for policy in policies]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing policies: {e}")
            span.record_exception(e)
            return []

def list_cloud_guard_problems(compartment_id: Optional[str] = None, lifecycle_state: str = "OPEN", time_window: str = "24h") -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_cloud_guard_problems", mcp_server="oci-mcp-security") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        cloud_guard_client = CloudGuardClient(config)
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
            return [{'id': p.id, 'risk_level': p.risk_level, 'description': getattr(p, 'description', ''), 'lifecycle_state': getattr(p, 'lifecycle_state', lifecycle_state)} for p in problems]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing Cloud Guard problems: {e}")
            span.record_exception(e)
            return []

def list_data_safe_findings(compartment_id: Optional[str] = None, profile: Optional[str] = None) -> List[Dict[str, Any]]:
    with tool_span(tracer, "list_data_safe_findings", mcp_server="oci-mcp-security") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        data_safe_client = DataSafeClient(config)
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(data_safe_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="DataSafe",
            oci_operation="ListFindings",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = list_call_get_all_results(data_safe_client.list_findings, compartment_id=compartment)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            findings = response.data
            # Convert findings to list format, handling the raw data structure
            result = []
            if findings:
                for finding in findings:
                    if hasattr(finding, '__dict__'):
                        result.append(dict(finding.__dict__))
                    else:
                        result.append({'raw_data': str(finding)})
            return result
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing Data Safe findings: {e}")
            span.record_exception(e)
            if e.status == 404:  # Data Safe not enabled
                return [{'error': 'Data Safe API not available. Please enable Data Safe in your tenancy. See: https://docs.oracle.com/en-us/iaas/data-safe/doc/getting-started-data-safe.html'}]
            return [{'error': str(e)}]

tools = [
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
            _start_http_server(int(os.getenv("METRICS_PORT", "8004")))
        except Exception:
            pass
    mcp = FastMCP(tools=tools, name="oci-mcp-security")
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
