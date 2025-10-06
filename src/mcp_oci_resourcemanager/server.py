"""MCP Server: OCI Resource Manager
"""

from typing import Any

from mcp_oci_common import make_client

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.resource_manager.ResourceManagerClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return []
