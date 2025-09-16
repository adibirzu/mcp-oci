"""MCP Server: OCI API Gateway
"""

from typing import Any

from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.apigateway.GatewayClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci:apigateway:list-gateways",
            "description": "List API Gateways in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "display_name": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["compartment_id"],
            },
            "handler": list_gateways,
        },
        {
            "name": "oci:apigateway:get-gateway",
            "description": "Get an API Gateway by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gateway_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["gateway_id"],
            },
            "handler": get_gateway,
        }
    ]


def list_gateways(compartment_id: str, display_name: str | None = None, limit: int | None = None,
                  page: str | None = None, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if display_name:
        kwargs["display_name"] = display_name
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_gateways(compartment_id=compartment_id, **kwargs)
    items = [g.__dict__ for g in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_gateway(gateway_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_gateway(gateway_id)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})
