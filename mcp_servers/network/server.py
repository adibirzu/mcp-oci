import os
import sys
import json
import logging
from typing import Dict, List, Any
from fastmcp import FastMCP
from fastmcp.tools import Tool
import oci
from oci.core import VirtualNetworkClient
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
vn_client = VirtualNetworkClient(config)

@with_oci_errors
def list_vcns(compartment_id: str = None) -> Dict[str, Any]:
    with tracer.start_as_current_span("list_vcns"):
        compartment_id = compartment_id or os.getenv('COMPARTMENT_OCID')
        vcns = vn_client.list_vcns(compartment_id=compartment_id).data
        return {
            'ok': True,
            'data': [{'display_name': vcn.display_name, 'id': vcn.id} for vcn in vcns]
        }

@with_oci_errors
def list_subnets(vcn_id: str) -> Dict[str, Any]:
    with tracer.start_as_current_span("list_subnets"):
        subnets = vn_client.list_subnets(vcn_id=vcn_id).data
        return {
            'ok': True,
            'data': [{'display_name': subnet.display_name, 'id': subnet.id, 'cidr_block': subnet.cidr_block} for subnet in subnets]
        }

@with_oci_errors
def summarize_public_endpoints(compartment_id: str = None) -> Dict[str, Any]:
    with tracer.start_as_current_span("summarize_public_endpoints"):
        compartment_id = compartment_id or os.getenv('COMPARTMENT_OCID')
        # Simplified summary - expand as needed
        vcns = vn_client.list_vcns(compartment_id=compartment_id).data
        public_endpoints = []
        for vcn in vcns:
            subnets = vn_client.list_subnets(vcn_id=vcn.id).data
            public_subnets = [s for s in subnets if s.prohibit_public_ip_on_vnic == False]
            if public_subnets:
                public_endpoints.append({
                    'vcn': vcn.display_name,
                    'public_subnets': len(public_subnets)
                })
        return {'ok': True, 'data': public_endpoints}

tools = [
    Tool.from_function(
        fn=list_vcns,
        name="list_vcns",
        description="List VCNs in a compartment"
    ),
    Tool.from_function(
        fn=list_subnets,
        name="list_subnets",
        description="List subnets in a VCN"
    ),
    Tool.from_function(
        fn=summarize_public_endpoints,
        name="summarize_public_endpoints",
        description="Summarize public endpoints in a compartment"
    ),
]

if __name__ == "__main__":
    mcp = FastMCP(tools=tools, name="oci-mcp-network")
    mcp.run()
