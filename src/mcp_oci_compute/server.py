"""MCP Server: OCI Compute

Exposes tools as `oci:compute:<action>`; read/list ops prioritized.
"""

from typing import Any, Dict, List, Optional
from mcp_oci_common import make_client

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: Optional[str] = None, region: Optional[str] = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.core.ComputeClient, profile=profile, region=region)


def register_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "oci:compute:list-instances",
            "description": "List compute instances in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "availability_domain": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_instances,
        },
        {
            "name": "oci:compute:list-images",
            "description": "List images in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "operating_system": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_images,
        },
        {
            "name": "oci:compute:list-vnics",
            "description": "List VNIC attachments for an instance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "instance_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "instance_id"],
            },
            "handler": list_vnics,
        },
        {
            "name": "oci:compute:get-instance",
            "description": "Get instance details by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instance_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["instance_id"],
            },
            "handler": get_instance,
        },
        {
            "name": "oci:compute:list-shapes",
            "description": "List compute shapes in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "availability_domain": {"type": "string"},
                    "image_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_shapes,
        },
        {
            "name": "oci:compute:instance-action",
            "description": "Perform an instance action (START, STOP, SOFTSTOP, RESET). Requires confirm=true; supports dry_run.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instance_id": {"type": "string"},
                    "action": {"type": "string", "enum": ["START", "STOP", "SOFTSTOP", "RESET"]},
                    "dry_run": {"type": "boolean", "default": False},
                    "confirm": {"type": "boolean", "default": False},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["instance_id", "action"],
            },
            "handler": instance_action,
            "mutating": True,
        },
    ]


def list_instances(compartment_id: str, availability_domain: Optional[str] = None,
                   limit: Optional[int] = None, page: Optional[str] = None,
                   profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if availability_domain:
        kwargs["availability_domain"] = availability_domain
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_instances(compartment_id=compartment_id, **kwargs)
    items = [i.data.__dict__ if hasattr(i, "data") else i.__dict__ for i in resp.data] if hasattr(resp, "data") else []
    next_page = getattr(resp, "opc_next_page", None)
    return {"items": items, "next_page": next_page}


def list_images(compartment_id: str, operating_system: Optional[str] = None,
                limit: Optional[int] = None, page: Optional[str] = None,
                profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if operating_system:
        kwargs["operating_system"] = operating_system
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_images(compartment_id=compartment_id, **kwargs)
    items = [i.__dict__ for i in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return {"items": items, "next_page": next_page}


def list_vnics(compartment_id: str, instance_id: str,
               limit: Optional[int] = None, page: Optional[str] = None,
               profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {"instance_id": instance_id}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_vnic_attachments(compartment_id=compartment_id, **kwargs)
    items = [a.__dict__ for a in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return {"items": items, "next_page": next_page}


def get_instance(instance_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_instance(instance_id)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return {"item": data}


def instance_action(instance_id: str, action: str, dry_run: bool = False, confirm: bool = False,
                    profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    if dry_run:
        return {"dry_run": True, "request": {"instance_id": instance_id, "action": action}}
    client = create_client(profile=profile, region=region)
    resp = client.instance_action(instance_id=instance_id, action=action)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return {"item": data}


def list_shapes(compartment_id: str, availability_domain: Optional[str] = None, image_id: Optional[str] = None,
                limit: Optional[int] = None, page: Optional[str] = None,
                profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if availability_domain:
        kwargs["availability_domain"] = availability_domain
    if image_id:
        kwargs["image_id"] = image_id
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_shapes(compartment_id=compartment_id, **kwargs)
    items = [s.__dict__ for s in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return {"items": items, "next_page": next_page}
