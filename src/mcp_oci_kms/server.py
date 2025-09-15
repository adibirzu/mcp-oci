"""MCP Server: OCI Key Management (KMS)
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
    return make_client(oci.key_management.KmsManagementClient, profile=profile, region=region)


def register_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "oci:kms:list-keys",
            "description": "List keys in a vault (management endpoint required).",
            "parameters": {
                "type": "object",
                "properties": {
                    "management_endpoint": {"type": "string"},
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["management_endpoint"],
            },
            "handler": list_keys,
        },
        {
            "name": "oci:kms:list-key-versions",
            "description": "List versions for a key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "management_endpoint": {"type": "string"},
                    "key_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["management_endpoint", "key_id"],
            },
            "handler": list_key_versions,
        }
    ]


def _kms_client(me: str, profile: Optional[str], region: Optional[str]):
    import oci
    cfg = oci.config.from_file(profile_name=profile)
    if region:
        cfg["region"] = region
    return oci.key_management.KmsManagementClient(config=cfg, service_endpoint=me)


def list_keys(management_endpoint: str, compartment_id: Optional[str] = None, limit: Optional[int] = None,
              page: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    kms = _kms_client(management_endpoint, profile, region)
    kwargs: Dict[str, Any] = {}
    if compartment_id:
        kwargs["compartment_id"] = compartment_id
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = kms.list_keys(**kwargs)
    items = [k.__dict__ for k in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_key_versions(management_endpoint: str, key_id: str, limit: Optional[int] = None, page: Optional[str] = None,
                      profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    kms = _kms_client(management_endpoint, profile, region)
    kwargs: Dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = kms.list_key_versions(key_id, **kwargs)
    items = [v.__dict__ for v in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)
