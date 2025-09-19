"""MCP Server: OCI Container Engine for Kubernetes (OKE)
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
    return make_client(oci.container_engine.ContainerEngineClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci:oke:list-clusters",
            "description": "List OKE clusters in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "name": {"type": "string"},
                    "lifecycle_state": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_clusters,
        },
        {
            "name": "oci:oke:list-node-pools",
            "description": "List node pools for a cluster.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "cluster_id": {"type": "string"},
                    "name": {"type": "string"},
                    "lifecycle_state": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "cluster_id"],
            },
            "handler": list_node_pools,
        },
        {
            "name": "oci:oke:get-cluster",
            "description": "Get OKE cluster by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cluster_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["cluster_id"],
            },
            "handler": get_cluster,
        },
        {
            "name": "oci:oke:get-node-pool",
            "description": "Get node pool by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_pool_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["node_pool_id"],
            },
            "handler": get_node_pool,
        }
    ]


def list_clusters(compartment_id: str, name: str | None = None, lifecycle_state: str | None = None,
                  limit: int | None = None, page: str | None = None,
                  profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    cache = get_cache()
    registry = get_registry()
    kwargs: dict[str, Any] = {}
    if name:
        kwargs["name"] = name
    if lifecycle_state:
        kwargs["lifecycle_state"] = lifecycle_state
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    cache_params = {"compartment_id": compartment_id, "name": name, "lifecycle_state": lifecycle_state, "limit": limit, "page": page}
    cached = cache.get("oke", "list_clusters", cache_params)
    if cached:
        return cached
    resp = client.list_clusters(compartment_id=compartment_id, **kwargs)
    items = [c.__dict__ for c in getattr(resp, "data", [])]
    if items:
        try:
            registry.update_clusters(compartment_id, items)
        except Exception:
            pass
    next_page = getattr(resp, "opc_next_page", None)
    out = with_meta(resp, {"items": items}, next_page=next_page)
    import os
    ttl = int(os.getenv("MCP_CACHE_TTL_OKE", os.getenv("MCP_CACHE_TTL", "1200")))
    cache.set("oke", "list_clusters", cache_params, out, ttl_seconds=ttl)
    return out


def get_cluster(cluster_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_cluster(cluster_id)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})


def get_node_pool(node_pool_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_node_pool(node_pool_id)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})


def list_node_pools(compartment_id: str, cluster_id: str, name: str | None = None,
                    lifecycle_state: str | None = None, limit: int | None = None, page: str | None = None,
                    profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    cache = get_cache()
    kwargs: dict[str, Any] = {"cluster_id": cluster_id}
    if name:
        kwargs["name"] = name
    if lifecycle_state:
        kwargs["lifecycle_state"] = lifecycle_state
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    cache_params = {"compartment_id": compartment_id, "cluster_id": cluster_id, "name": name, "lifecycle_state": lifecycle_state, "limit": limit, "page": page}
    cached = cache.get("oke", "list_node_pools", cache_params)
    if cached:
        return cached
    resp = client.list_node_pools(compartment_id=compartment_id, **kwargs)
    items = [np.__dict__ for np in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    out = with_meta(resp, {"items": items}, next_page=next_page)
    import os
    ttl = int(os.getenv("MCP_CACHE_TTL_OKE", os.getenv("MCP_CACHE_TTL", "1200")))
    cache.set("oke", "list_node_pools", cache_params, out, ttl_seconds=ttl)
    return out
