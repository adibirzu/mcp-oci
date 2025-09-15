"""
FastMCP wrapper for optimized Object Storage REST API service
Minimal token usage with direct REST API calls
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastmcp.server import FastMCP

from mcp_oci_rest.objectstorage import (
    list_buckets,
    get_bucket,
    list_objects,
    get_object,
    get_namespace,
    get_server_info as rest_get_server_info,
)


def run_objectstorage_rest(profile: str | None = None, region: str | None = None, server_name: str = "oci-objectstorage-rest"):
    """Run optimized Object Storage FastMCP server with REST API"""
    app = FastMCP(server_name)

    def _with_defaults(kwargs: dict[str, Any]) -> dict[str, Any]:
        if profile and "profile" not in kwargs:
            kwargs["profile"] = profile
        if region and "region" not in kwargs:
            kwargs["region"] = region
        return kwargs

    @app.tool()
    async def oci_objectstorage_list_buckets(
        namespace: str,
        compartment_id: str,
        limit: int | None = None,
        page: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """List object storage buckets using optimized REST API"""
        args = {
            "namespace": namespace,
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        return list_buckets(**_with_defaults(args))

    @app.tool()
    async def oci_objectstorage_get_bucket(
        namespace: str,
        bucket_name: str,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Get specific bucket using optimized REST API"""
        args = {
            "namespace": namespace,
            "bucket_name": bucket_name,
            "profile": profile,
            "region": region,
        }
        return get_bucket(**_with_defaults(args))

    @app.tool()
    async def oci_objectstorage_list_objects(
        namespace: str,
        bucket_name: str,
        prefix: str | None = None,
        limit: int | None = None,
        page: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """List objects in bucket using optimized REST API"""
        args = {
            "namespace": namespace,
            "bucket_name": bucket_name,
            "prefix": prefix,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        return list_objects(**_with_defaults(args))

    @app.tool()
    async def oci_objectstorage_get_object(
        namespace: str,
        bucket_name: str,
        object_name: str,
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Get object metadata using optimized REST API"""
        args = {
            "namespace": namespace,
            "bucket_name": bucket_name,
            "object_name": object_name,
            "profile": profile,
            "region": region,
        }
        return get_object(**_with_defaults(args))

    @app.tool()
    async def oci_objectstorage_get_namespace(
        profile: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Get object storage namespace using optimized REST API"""
        args = {
            "profile": profile,
            "region": region,
        }
        return get_namespace(**_with_defaults(args))

    @app.tool()
    async def get_server_info() -> dict[str, Any]:
        """Get server information"""
        info = rest_get_server_info()
        info["fastmcp_wrapper"] = True
        info["optimization"] = "REST API with minimal tokens"
        return info

    app.run()
