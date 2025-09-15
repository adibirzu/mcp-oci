"""MCP Server: OCI Limits and Quotas (Cost Control)

Exposes tools as `oci:limits:<action>` and `oci:quotas:<action>`.
"""

from typing import Any, Dict, List, Optional
from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client_limits(profile: Optional[str] = None, region: Optional[str] = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.limits.LimitsClient, profile=profile, region=region)


def create_client_quotas(profile: Optional[str] = None, region: Optional[str] = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.limits.QuotasClient, profile=profile, region=region)


def register_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "oci:limits:list-services",
            "description": "List services with limits for a compartment.",
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
            "handler": list_services,
        },
        {
            "name": "oci:limits:list-limit-values",
            "description": "List limit values for a service in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "service_name": {"type": "string"},
                    "scope_type": {"type": "string", "enum": ["REGION", "AD"]},
                    "availability_domain": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "service_name"],
            },
            "handler": list_limit_values,
        },
        {
            "name": "oci:quotas:list-quotas",
            "description": "List quotas in a compartment.",
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
            "handler": list_quotas,
        },
        {
            "name": "oci:quotas:get-quota",
            "description": "Get a quota by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quota_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["quota_id"],
            },
            "handler": get_quota,
        },
    ]


def list_services(compartment_id: str, limit: Optional[int] = None, page: Optional[str] = None,
                  profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client_limits(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_services(compartment_id=compartment_id, **kwargs)
    items = [s.__dict__ for s in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_limit_values(compartment_id: str, service_name: str, scope_type: Optional[str] = None,
                      availability_domain: Optional[str] = None, limit: Optional[int] = None,
                      page: Optional[str] = None, profile: Optional[str] = None,
                      region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client_limits(profile=profile, region=region)
    kwargs: Dict[str, Any] = {"service_name": service_name}
    if scope_type:
        kwargs["scope_type"] = scope_type
    if availability_domain:
        kwargs["availability_domain"] = availability_domain
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_limit_values(compartment_id=compartment_id, **kwargs)
    items = [v.__dict__ for v in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_quotas(compartment_id: str, limit: Optional[int] = None, page: Optional[str] = None,
                profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client_quotas(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_quotas(compartment_id=compartment_id, **kwargs)
    items = [q.__dict__ for q in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_quota(quota_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client_quotas(profile=profile, region=region)
    resp = client.get_quota(quota_id)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})
