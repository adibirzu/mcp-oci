"""
Optimized FastMCP wrapper for IAM
Provides clear, Claude-friendly responses
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

try:
    from fastmcp import FastMCP
except ImportError:
    print("fastmcp not available. Install with: pip install fastmcp", file=sys.stderr)
    sys.exit(1)

from mcp_oci_iam.server_optimized import (
    list_users,
    get_user,
    list_compartments,
    list_groups,
    list_policies,
)


def run_iam_optimized(profile: Optional[str] = None, region: Optional[str] = None, 
                      server_name: str = "oci-iam-optimized"):
    """Run the optimized IAM FastMCP server."""
    app = FastMCP(server_name)

    def _with_defaults(kwargs):
        if profile and "profile" not in kwargs:
            kwargs["profile"] = profile
        if region and "region" not in kwargs:
            kwargs["region"] = region
        return kwargs

    @app.tool()
    async def oci_iam_list_users(
        compartment_id: str, 
        name: str = None, 
        limit: int = None, 
        page: str = None,
        profile: str = None, 
        region: str = None
    ):
        """List IAM users in a compartment with clear, readable response."""
        args = {
            "compartment_id": compartment_id,
            "name": name,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_users(**args)

    @app.tool()
    async def oci_iam_get_user(
        user_id: str, 
        profile: str = None, 
        region: str = None
    ):
        """Get specific IAM user details with clear response."""
        args = {
            "user_id": user_id,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return get_user(**args)

    @app.tool()
    async def oci_iam_list_compartments(
        compartment_id: str, 
        include_subtree: bool = True, 
        access_level: str = "ANY",
        limit: int = None, 
        page: str = None,
        profile: str = None, 
        region: str = None
    ):
        """List compartments with clear, readable response. Shows hierarchy and access levels."""
        args = {
            "compartment_id": compartment_id,
            "include_subtree": include_subtree,
            "access_level": access_level,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_compartments(**args)

    @app.tool()
    async def oci_iam_list_groups(
        compartment_id: str, 
        limit: int = None, 
        page: str = None,
        profile: str = None, 
        region: str = None
    ):
        """List IAM groups in a compartment with clear response."""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_groups(**args)

    @app.tool()
    async def oci_iam_list_policies(
        compartment_id: str, 
        limit: int = None, 
        page: str = None,
        profile: str = None, 
        region: str = None
    ):
        """List IAM policies in a compartment with clear response."""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_policies(**args)

    @app.tool()
    async def get_server_info():
        return {
            "name": server_name,
            "framework": "fastmcp",
            "service": "iam",
            "optimized": True,
            "features": [
                "Clear, Claude-friendly responses",
                "Structured data with helpful messages",
                "Better error handling and user guidance",
                "Consistent response format across all tools"
            ],
            "defaults": {"profile": profile, "region": region},
        }

    app.run()
