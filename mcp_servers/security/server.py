import os
import sys
import logging
from typing import Dict, List, Any
from fastmcp import FastMCP
from fastmcp.tools import Tool
import oci
from oci.identity import IdentityClient
from oci.cloud_guard import CloudGuardClient
from oci.data_safe import DataSafeClient
from mcp_oci_common import get_oci_config, with_oci_errors
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Set up tracing
if not trace.get_tracer_provider():
    trace.set_tracer_provider(TracerProvider())
    otlp_exporter = OTLPSpanExporter(endpoint=os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317'))
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
tracer = trace.get_tracer(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)
logger = logging.getLogger(__name__)

config = get_oci_config()
identity_client = IdentityClient(config)
cloud_guard_client = CloudGuardClient(config)
data_safe_client = DataSafeClient(config)

@with_oci_errors
def list_iam_users(compartment_id: str = None) -> Dict[str, Any]:
    with tracer.start_as_current_span("list_iam_users"):
        compartment_id = compartment_id or os.getenv('COMPARTMENT_OCID')
        users = identity_client.list_users(compartment_id=compartment_id).data
        return {
            'ok': True,
            'data': [{'name': user.name, 'id': user.id} for user in users]
        }

@with_oci_errors
def list_groups(compartment_id: str = None) -> Dict[str, Any]:
    with tracer.start_as_current_span("list_groups"):
        compartment_id = compartment_id or os.getenv('COMPARTMENT_OCID')
        groups = identity_client.list_groups(compartment_id=compartment_id).data
        return {
            'ok': True,
            'data': [{'name': group.name, 'id': group.id} for group in groups]
        }

@with_oci_errors
def list_policies(compartment_id: str = None) -> Dict[str, Any]:
    with tracer.start_as_current_span("list_policies"):
        compartment_id = compartment_id or os.getenv('COMPARTMENT_OCID')
        policies = identity_client.list_policies(compartment_id=compartment_id).data
        return {
            'ok': True,
            'data': [{'name': policy.name, 'id': policy.id} for policy in policies]
        }

@with_oci_errors
def list_cloud_guard_problems(compartment_id: str = None, lifecycle_state: str = "OPEN", time_window: str = "24h") -> Dict[str, Any]:
    with tracer.start_as_current_span("list_cloud_guard_problems"):
        compartment_id = compartment_id or os.getenv('COMPARTMENT_OCID')
        problems = cloud_guard_client.list_problems(compartment_id=compartment_id, lifecycle_state=lifecycle_state).data
        return {
            'ok': True,
            'data': [{'id': p.id, 'risk_level': p.risk_level, 'description': p.description} for p in problems]
        }

@with_oci_errors
def list_data_safe_findings(compartment_id: str = None, profile: str = None) -> Dict[str, Any]:
    with tracer.start_as_current_span("list_data_safe_findings"):
        compartment_id = compartment_id or os.getenv('COMPARTMENT_OCID')
        try:
            findings = data_safe_client.list_findings(compartment_id=compartment_id).data
            return {'ok': True, 'data': findings}
        except oci.exceptions.ServiceError as e:
            if e.status == 404:  # Data Safe not enabled
                return {'ok': False, 'error': 'Data Safe API not available. Please enable Data Safe in your tenancy. See: https://docs.oracle.com/en-us/iaas/data-safe/doc/getting-started-data-safe.html'}
            raise

tools = [
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
    mcp = FastMCP(tools=tools, name="oci-mcp-security")
    mcp.run()
