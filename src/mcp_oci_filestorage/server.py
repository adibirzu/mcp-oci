"""MCP Server: OCI File Storage (FSS)
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
    return make_client(oci.file_storage.FileStorageClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci_filestorage_list_file_systems",
            "description": "List File Systems in a compartment and availability domain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "availability_domain": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "availability_domain"],
            },
            "handler": list_file_systems,
        },
        {
            "name": "oci_filestorage_list_mount_targets",
            "description": "List Mount Targets in a compartment and availability domain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "availability_domain": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "availability_domain"],
            },
            "handler": list_mount_targets,
        }
    ]


def list_file_systems(compartment_id: str, availability_domain: str, limit: int | None = None,
                      page: str | None = None, profile: str | None = None,
                      region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_file_systems(compartment_id=compartment_id, availability_domain=availability_domain, **kwargs)
    items = [fs.__dict__ for fs in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_mount_targets(compartment_id: str, availability_domain: str, limit: int | None = None,
                       page: str | None = None, profile: str | None = None,
                       region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_mount_targets(compartment_id=compartment_id, availability_domain=availability_domain, **kwargs)
    items = [mt.__dict__ for mt in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)
