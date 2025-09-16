"""MCP Server: OCI Streaming
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
    return make_client(oci.streaming.StreamAdminClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci:streaming:list-streams",
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
            "name": "oci:streaming:get-stream",
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
    kwargs: dict[str, Any] = {}
    if name:
        kwargs["name"] = name
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_streams(compartment_id=compartment_id, **kwargs)
    items = [s.__dict__ for s in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_stream(stream_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_stream(stream_id)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})
