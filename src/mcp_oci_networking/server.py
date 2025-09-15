"""MCP Server: OCI Networking (VCN)

Exposes tools as `oci:networking:<action>`.
"""

from typing import Any, Dict, List, Optional
from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: Optional[str] = None, region: Optional[str] = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.core.VirtualNetworkClient, profile=profile, region=region)


def register_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "oci:networking:list-subnets",
            "description": "List subnets in a compartment; optionally filter by VCN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "vcn_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_subnets,
        },
        {
            "name": "oci:networking:list-vcns",
            "description": "List VCNs in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_vcns,
        },
        {
            "name": "oci:networking:list-vcns-by-dns",
            "description": "List VCNs filtered by dns_label (client-side filter).",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "dns_label": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "dns_label"],
            },
            "handler": list_vcns_by_dns,
        },
        {
            "name": "oci:networking:list-route-tables",
            "description": "List route tables in a compartment; optionally filter by VCN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "vcn_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_route_tables,
        },
        {
            "name": "oci:networking:list-security-lists",
            "description": "List security lists in a compartment; optionally filter by VCN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "vcn_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_security_lists,
        },
        {
            "name": "oci:networking:create-vcn",
            "description": "Create a VCN (confirm=true supports required; dry_run available).",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "cidr_block": {"type": "string"},
                    "display_name": {"type": "string"},
                    "dns_label": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": False},
                    "confirm": {"type": "boolean", "default": False},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "cidr_block", "display_name"],
            },
            "handler": create_vcn,
            "mutating": True,
        },
        {
            "name": "oci:networking:list-network-security-groups",
            "description": "List Network Security Groups (NSGs) in a compartment; optional VCN filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "vcn_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_nsgs,
        },
    ]


def list_subnets(compartment_id: str, vcn_id: Optional[str] = None,
                 limit: Optional[int] = None, page: Optional[str] = None,
                 profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if vcn_id:
        kwargs["vcn_id"] = vcn_id
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_subnets(compartment_id=compartment_id, **kwargs)
    items = [s.__dict__ for s in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_nsgs(compartment_id: str, vcn_id: Optional[str] = None, limit: Optional[int] = None,
              page: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if vcn_id:
        kwargs["vcn_id"] = vcn_id
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_network_security_groups(compartment_id=compartment_id, **kwargs)
    items = [n.__dict__ for n in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_vcns(compartment_id: str, limit: Optional[int] = None, page: Optional[str] = None,
              profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_vcns(compartment_id=compartment_id, **kwargs)
    items = [v.__dict__ for v in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_vcns_by_dns(compartment_id: str, dns_label: str, limit: Optional[int] = None, page: Optional[str] = None,
                     profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    out = list_vcns(compartment_id=compartment_id, limit=limit, page=page, profile=profile, region=region)
    items = [v for v in out.get("items", []) if (v.get("dns_label") if isinstance(v, dict) else getattr(v, "dns_label", None)) == dns_label]
    return {"items": items, "next_page": out.get("next_page")}


def list_route_tables(compartment_id: str, vcn_id: Optional[str] = None,
                      limit: Optional[int] = None, page: Optional[str] = None,
                      profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if vcn_id:
        kwargs["vcn_id"] = vcn_id
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_route_tables(compartment_id=compartment_id, **kwargs)
    items = [r.__dict__ for r in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_security_lists(compartment_id: str, vcn_id: Optional[str] = None,
                        limit: Optional[int] = None, page: Optional[str] = None,
                        profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if vcn_id:
        kwargs["vcn_id"] = vcn_id
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_security_lists(compartment_id=compartment_id, **kwargs)
    items = [s.__dict__ for s in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def create_vcn(compartment_id: str, cidr_block: str, display_name: str, dns_label: Optional[str] = None,
               dry_run: bool = False, confirm: bool = False, profile: Optional[str] = None,
               region: Optional[str] = None) -> Dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    details = {
        "compartment_id": compartment_id,
        "cidr_block": cidr_block,
        "display_name": display_name,
    }
    if dns_label:
        details["dns_label"] = dns_label
    if dry_run:
        return {"dry_run": True, "request": details}
    model = oci.core.models.CreateVcnDetails(**details)  # type: ignore
    client = create_client(profile=profile, region=region)
    resp = client.create_vcn(create_vcn_details=model)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})
