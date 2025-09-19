"""MCP Server: OCI Load Balancer
"""

from typing import Any

from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta
from mcp_oci_common.cache import get_cache
from mcp_oci_common.name_registry import get_registry

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.load_balancer.LoadBalancerClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
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


def list_load_balancers(compartment_id: str, limit: int | None = None, page: str | None = None,
                        profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    cache = get_cache()
    registry = get_registry()
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    cache_params = {"compartment_id": compartment_id, "limit": limit, "page": page}
    cached = cache.get("loadbalancer", "list_load_balancers", cache_params)
    if cached:
        return cached
    resp = client.list_load_balancers(compartment_id=compartment_id, **kwargs)
    items = [l.__dict__ for l in getattr(resp, "data", [])]
    # Record LB names in the registry (reuse streams/application map as generic store)
    if items:
        try:
            registry.update_streams(compartment_id, [{"id": i.get("id"), "name": i.get("display_name") or i.get("name")} for i in items])
        except Exception:
            pass
    next_page = getattr(resp, "opc_next_page", None)
    out = with_meta(resp, {"items": items}, next_page=next_page)
    import os
    ttl = int(os.getenv("MCP_CACHE_TTL_LOADBALANCER", os.getenv("MCP_CACHE_TTL", "1800")))
    cache.set("loadbalancer", "list_load_balancers", cache_params, out, ttl_seconds=ttl)
    return out


def get_backend_health(load_balancer_id: str, backend_set_name: str,
                       profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_backend_set_health(load_balancer_id=load_balancer_id, backend_set_name=backend_set_name)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})
