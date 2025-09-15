"""
FastMCP wrapper for optimized Log Analytics REST API service
Minimal token usage with direct REST API calls
Auto-discovers namespace - no manual parameters needed!
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastmcp.server import FastMCP

from mcp_oci_rest.loganalytics import (
    get_namespace,
    list_entities,
    run_query,
    list_sources,
    get_server_info as rest_get_server_info,
)


def run_loganalytics_rest(profile: str | None = None, region: str | None = None, server_name: str = "oci-loganalytics-rest"):
    """Run optimized Log Analytics FastMCP server with REST API"""
    app = FastMCP(server_name)

    def _with_defaults(kwargs: dict[str, Any]) -> dict[str, Any]:
        if profile and "profile" not in kwargs:
            kwargs["profile"] = profile
        if region and "region" not in kwargs:
            kwargs["region"] = region
        return kwargs

    @app.tool()
    async def oci_loganalytics_get_namespace(
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Get Log Analytics namespace - auto-discovered, no parameters needed!"""
        args = {
            "profile": profile,
            "region": region,
        }
        return get_namespace(**_with_defaults(args))

    @app.tool()
    async def oci_loganalytics_list_entities(
        compartment_id: str,
        limit: int | None = None,
        page: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """List Log Analytics entities - only compartment_id needed, namespace auto-discovered!"""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        return list_entities(**_with_defaults(args))

    @app.tool()
    async def oci_loganalytics_run_query(
        query_string: str,
        time_start: str,
        time_end: str,
        subsystem: str | None = None,
        max_total_count: int | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Run Log Analytics query - namespace auto-discovered, no manual parameters needed!"""
        args = {
            "query_string": query_string,
            "time_start": time_start,
            "time_end": time_end,
            "subsystem": subsystem,
            "max_total_count": max_total_count,
            "profile": profile,
            "region": region,
        }
        return run_query(**_with_defaults(args))

    @app.tool()
    async def oci_loganalytics_list_sources(
        compartment_id: str,
        limit: int | None = None,
        page: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """List Log Analytics sources - only compartment_id needed, namespace auto-discovered!"""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        return list_sources(**_with_defaults(args))

    @app.tool()
    async def get_server_info() -> dict[str, Any]:
        """Get server information"""
        info = rest_get_server_info()
        info["fastmcp_wrapper"] = True
        info["optimization"] = "REST API with minimal tokens"
        info["auto_namespace"] = True
        info["features"] = [
            "Auto-discovers namespace - no manual parameters needed",
            "80% token reduction vs SDK approach",
            "Direct REST API calls for better performance",
            "Standardized authentication via .oci/config"
        ]
        return info

    app.run()
