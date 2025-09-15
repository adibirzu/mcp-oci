"""MCP Server: OCI Block Storage
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
    return make_client(oci.core.BlockstorageClient, profile=profile, region=region)


def list_volumes(compartment_id: str, availability_domain: Optional[str] = None,
                display_name: Optional[str] = None, lifecycle_state: Optional[str] = None,
                limit: Optional[int] = None, page: Optional[str] = None,
                profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    """List block volumes in a compartment."""
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {"compartment_id": compartment_id}
    if availability_domain:
        kwargs["availability_domain"] = availability_domain
    if display_name:
        kwargs["display_name"] = display_name
    if lifecycle_state:
        kwargs["lifecycle_state"] = lifecycle_state
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    
    resp = client.list_volumes(**kwargs)
    items = [v.__dict__ for v in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_volume(volume_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    """Get block volume details by OCID."""
    client = create_client(profile=profile, region=region)
    resp = client.get_volume(volume_id=volume_id)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})


def list_volume_backups(compartment_id: str, volume_id: Optional[str] = None,
                       display_name: Optional[str] = None, lifecycle_state: Optional[str] = None,
                       limit: Optional[int] = None, page: Optional[str] = None,
                       profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    """List volume backups in a compartment."""
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {"compartment_id": compartment_id}
    if volume_id:
        kwargs["volume_id"] = volume_id
    if display_name:
        kwargs["display_name"] = display_name
    if lifecycle_state:
        kwargs["lifecycle_state"] = lifecycle_state
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    
    resp = client.list_volume_backups(**kwargs)
    items = [vb.__dict__ for vb in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_volume_backup(volume_backup_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    """Get volume backup details by OCID."""
    client = create_client(profile=profile, region=region)
    resp = client.get_volume_backup(volume_backup_id=volume_backup_id)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})


def register_tools() -> List[Dict[str, Any]]:
    return []
