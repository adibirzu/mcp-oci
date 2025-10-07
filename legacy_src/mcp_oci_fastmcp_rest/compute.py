"""
FastMCP wrapper for optimized Compute REST API service
Minimal token usage with direct REST API calls
"""

from __future__ import annotations

from typing import Any

from fastmcp.server import FastMCP

from mcp_oci_rest.compute import (
    get_instance,
    list_instances,
    list_running_instances,
    list_stopped_instances,
    search_instances,
)
from mcp_oci_rest.compute import (
    get_server_info as rest_get_server_info,
)


def run_compute_rest(profile: str | None = None, region: str | None = None, server_name: str = "oci-compute-rest"):
    """Run optimized Compute FastMCP server with REST API"""
    app = FastMCP(server_name)

    def _with_defaults(kwargs: dict[str, Any]) -> dict[str, Any]:
        if profile and "profile" not in kwargs:
            kwargs["profile"] = profile
        if region and "region" not in kwargs:
            kwargs["region"] = region
        return kwargs

    @app.tool()
    async def oci_compute_list_instances(
        compartment_id: str,
        limit: int | None = None,
        page: str | None = None,
        lifecycle_state: str | None = None,
        display_name: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """List compute instances using optimized REST API"""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "lifecycle_state": lifecycle_state,
            "display_name": display_name,
            "profile": profile,
            "region": region,
        }
        return list_instances(**_with_defaults(args))

    @app.tool()
    async def oci_compute_get_instance(
        instance_id: str,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Get specific compute instance using optimized REST API"""
        args = {
            "instance_id": instance_id,
            "profile": profile,
            "region": region,
        }
        return get_instance(**_with_defaults(args))

    @app.tool()
    async def oci_compute_list_stopped_instances(
        compartment_id: str,
        limit: int | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """List stopped instances using optimized REST API"""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "profile": profile,
            "region": region,
        }
        return list_stopped_instances(**_with_defaults(args))

    @app.tool()
    async def oci_compute_list_running_instances(
        compartment_id: str,
        limit: int | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """List running instances using optimized REST API"""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "profile": profile,
            "region": region,
        }
        return list_running_instances(**_with_defaults(args))

    @app.tool()
    async def oci_compute_search_instances(
        compartment_id: str,
        query: str,
        limit: int | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Search instances using optimized REST API"""
        args = {
            "compartment_id": compartment_id,
            "query": query,
            "limit": limit,
            "profile": profile,
            "region": region,
        }
        return search_instances(**_with_defaults(args))

    @app.tool()
    async def get_server_info() -> dict[str, Any]:
        """Get server information"""
        info = rest_get_server_info()
        info["fastmcp_wrapper"] = True
        info["optimization"] = "REST API with minimal tokens"
        return info

    app.run()
