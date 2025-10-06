"""MCP Server: OCI DNS
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
    return make_client(oci.dns.DnsClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci_dns_list_zones",
            "description": "List DNS zones in a compartment.",
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
            "handler": list_zones,
        },
        {
            "name": "oci_dns_list_rrset",
            "description": "List record set (RRSet) for a zone and domain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone_name_or_id": {"type": "string"},
                    "domain": {"type": "string"},
                    "rtype": {"type": "string", "description": "Record type, e.g., A, CNAME"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["zone_name_or_id", "domain"],
            },
            "handler": list_rrset,
        },
    ]


def list_zones(compartment_id: str, limit: int | None = None, page: str | None = None,
               profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_zones(compartment_id=compartment_id, **kwargs)
    items = [z.__dict__ for z in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_rrset(zone_name_or_id: str, domain: str, rtype: str | None = None,
               profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    if rtype:
        resp = client.get_rr_set(zone_name_or_id=zone_name_or_id, domain=domain, rtype=rtype)
        items = [r.__dict__ for r in getattr(resp, "data", [])]
        return with_meta(resp, {"items": items})
    # If type not provided, list all records via get_zone_records
    resp = client.get_zone_records(zone_name_or_id)
    records = getattr(resp, "data", None)
    if records and hasattr(records, "items"):
        items = [r.__dict__ for r in records.items]
    else:
        items = [getattr(records, "__dict__", records)] if records else []
    return with_meta(resp, {"items": items})
