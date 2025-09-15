"""MCP Server: OCI Functions
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
    return make_client(oci.functions.FunctionsManagementClient, profile=profile, region=region)


def register_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "oci:functions:list-applications",
            "description": "List Functions applications in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "display_name": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_applications,
        },
        {
            "name": "oci:functions:list-functions",
            "description": "List functions in an application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {"type": "string"},
                    "display_name": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["application_id"],
            },
            "handler": list_functions,
        },
        {
            "name": "oci:functions:get-application",
            "description": "Get application by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["application_id"],
            },
            "handler": get_application,
        },
        {
            "name": "oci:functions:get-function",
            "description": "Get function by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["function_id"],
            },
            "handler": get_function,
        },
        {
            "name": "oci:functions:list-triggers",
            "description": "List triggers for an application (if supported by SDK).",
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["application_id"],
            },
            "handler": list_triggers,
        },
    ]


def list_applications(compartment_id: str, display_name: Optional[str] = None, limit: Optional[int] = None,
                      page: Optional[str] = None, profile: Optional[str] = None,
                      region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if display_name:
        kwargs["display_name"] = display_name
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_applications(compartment_id=compartment_id, **kwargs)
    items = [a.__dict__ for a in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_functions(application_id: str, display_name: Optional[str] = None, limit: Optional[int] = None,
                   page: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if display_name:
        kwargs["display_name"] = display_name
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_functions(application_id=application_id, **kwargs)
    items = [f.__dict__ for f in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_application(application_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_application(application_id)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})


def get_function(function_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_function(function_id)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})


def list_triggers(application_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    method = getattr(client, "list_triggers", None)
    if method is None:
        raise RuntimeError("list_triggers not available in this SDK/version")
    resp = method(application_id=application_id)
    items = [t.__dict__ for t in getattr(resp, "data", [])]
    return with_meta(resp, {"items": items})
