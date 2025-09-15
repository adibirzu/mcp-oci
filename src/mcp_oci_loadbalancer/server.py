"""MCP Server: OCI Load Balancer
"""

from typing import Any, Dict, List, Optional
from mcp_oci_common.response import with_meta
from mcp_oci_common import make_client

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: Optional[str] = None, region: Optional[str] = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.load_balancer.LoadBalancerClient, profile=profile, region=region)


def register_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "oci:loadbalancer:list-load-balancers",
            "description": "List Load Balancers in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_load_balancers,
        },
        {
            "name": "oci:loadbalancer:get-backend-health",
            "description": "Get backend set health for a Load Balancer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "load_balancer_id": {"type": "string"},
                    "backend_set_name": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["load_balancer_id", "backend_set_name"],
            },
            "handler": get_backend_health,
        },
    ]


def list_load_balancers(compartment_id: str, limit: Optional[int] = None, page: Optional[str] = None,
                        profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_load_balancers(compartment_id=compartment_id, **kwargs)
    items = [l.__dict__ for l in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_backend_health(load_balancer_id: str, backend_set_name: str,
                       profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_backend_set_health(load_balancer_id=load_balancer_id, backend_set_name=backend_set_name)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})
