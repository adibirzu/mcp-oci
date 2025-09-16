"""
FastMCP wrapper for optimized IAM REST API service
Minimal token usage with direct REST API calls
"""

from __future__ import annotations

from typing import Any

from fastmcp.server import FastMCP

from mcp_oci_rest.iam import (
    get_compartment,
    get_user,
    list_compartments,
    list_groups,
    list_policies,
    list_users,
)
from mcp_oci_rest.iam import (
    get_server_info as rest_get_server_info,
)


def run_iam_rest(profile: str | None = None, region: str | None = None, server_name: str = "oci-iam-rest"):
    """Run optimized IAM FastMCP server with REST API"""
    app = FastMCP(server_name)

    def _with_defaults(kwargs: dict[str, Any]) -> dict[str, Any]:
        if profile and "profile" not in kwargs:
            kwargs["profile"] = profile
        if region and "region" not in kwargs:
            kwargs["region"] = region
        return kwargs

    @app.tool()
    async def oci_iam_list_users(
        compartment_id: str,
        limit: int | None = None,
        page: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """List IAM users using optimized REST API"""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        return list_users(**_with_defaults(args))

    @app.tool()
    async def oci_iam_get_user(
        user_id: str,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Get specific IAM user using optimized REST API"""
        args = {
            "user_id": user_id,
            "profile": profile,
            "region": region,
        }
        return get_user(**_with_defaults(args))

    @app.tool()
    async def oci_iam_list_compartments(
        compartment_id: str,
        limit: int | None = None,
        page: str | None = None,
        access_level: str = "ANY",
        compartment_id_in_subtree: bool = False,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """List compartments using optimized REST API"""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "access_level": access_level,
            "compartment_id_in_subtree": compartment_id_in_subtree,
            "profile": profile,
            "region": region,
        }
        return list_compartments(**_with_defaults(args))

    @app.tool()
    async def oci_iam_get_compartment(
        compartment_id: str,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Get specific compartment using optimized REST API"""
        args = {
            "compartment_id": compartment_id,
            "profile": profile,
            "region": region,
        }
        return get_compartment(**_with_defaults(args))

    @app.tool()
    async def oci_iam_list_groups(
        compartment_id: str,
        limit: int | None = None,
        page: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """List IAM groups using optimized REST API"""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        return list_groups(**_with_defaults(args))

    @app.tool()
    async def oci_iam_list_policies(
        compartment_id: str,
        limit: int | None = None,
        page: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """List IAM policies using optimized REST API"""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        return list_policies(**_with_defaults(args))

    @app.tool()
    async def get_server_info() -> dict[str, Any]:
        """Get server information"""
        info = rest_get_server_info()
        info["fastmcp_wrapper"] = True
        info["optimization"] = "REST API with minimal tokens"
        return info

    app.run()
