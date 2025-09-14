"""MCP Server: OCI DNS
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
    return make_client(oci.dns.DnsClient, profile=profile, region=region)


def register_tools() -> List[Dict[str, Any]]:
    return []
