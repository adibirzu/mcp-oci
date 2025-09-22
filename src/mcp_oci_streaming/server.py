"""MCP Server: OCI Streaming
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
    return make_client(oci.streaming.StreamAdminClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci_streaming_list_streams",
            "description": "List streams in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "name": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["compartment_id"],
            },
            "handler": list_streams,
        },
        {
            "name": "oci_streaming_get_stream",
            "description": "Get stream by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stream_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["stream_id"],
            },
            "handler": get_stream,
        }
    ]


def list_streams(compartment_id: str, name: str | None = None, limit: int | None = None,
                 page: str | None = None, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    cache = get_cache()
    registry = get_registry()
    kwargs: dict[str, Any] = {}
    if name:
        kwargs["name"] = name
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    cache_params = {"compartment_id": compartment_id, "name": name, "limit": limit, "page": page}
    cached = cache.get("streaming", "list_streams", cache_params)
    if cached:
        return cached
    resp = client.list_streams(compartment_id=compartment_id, **kwargs)
    items = [s.__dict__ for s in getattr(resp, "data", [])]
    if items:
        try:
            registry.update_streams(compartment_id, items)
        except Exception:
            pass
    next_page = getattr(resp, "opc_next_page", None)
    out = with_meta(resp, {"items": items}, next_page=next_page)
    import os
    ttl = int(os.getenv("MCP_CACHE_TTL_STREAMING", os.getenv("MCP_CACHE_TTL", "1200")))
    cache.set("streaming", "list_streams", cache_params, out, ttl_seconds=ttl)
    return out


def get_stream(stream_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_stream(stream_id)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})
