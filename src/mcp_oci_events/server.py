"""MCP Server: OCI Events
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
    return make_client(oci.events.EventsClient, profile=profile, region=region)


def register_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "oci:events:list-rules",
            "description": "List Event Rules in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "lifecycle_state": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["compartment_id"],
            },
            "handler": list_rules,
        },
        {
            "name": "oci:events:get-rule",
            "description": "Get Event Rule by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["rule_id"],
            },
            "handler": get_rule,
        }
    ]


def list_rules(compartment_id: str, lifecycle_state: Optional[str] = None, limit: Optional[int] = None,
               page: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {}
    if lifecycle_state:
        kwargs["lifecycle_state"] = lifecycle_state
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_rules(compartment_id=compartment_id, **kwargs)
    items = [r.__dict__ for r in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_rule(rule_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_rule(rule_id)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})
