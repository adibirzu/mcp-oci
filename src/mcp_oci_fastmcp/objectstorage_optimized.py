#!/usr/bin/env python3
"""
Optimized Objectstorage MCP Server
Based on official OCI Python SDK patterns and shared architecture
"""

from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None

from .shared_architecture import (
    clients,
    OCIResponse,
    handle_oci_error,
    format_for_llm,
    validate_compartment_id,
    create_fastmcp_tool,
    create_common_tools
)

def run_objectstorage(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_objectstorage") -> None:
    """Serve an optimized FastMCP app for objectstorage operations."""
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )

    # Set environment variables if provided
    if profile:
        import os
        os.environ["OCI_PROFILE"] = profile
    if region:
        import os
        os.environ["OCI_REGION"] = region

    app = FastMCP(server_name)

    # Create common tools
    create_common_tools(app, server_name)

    # Object Storage-specific tools
    @app.tool()
    async def get_namespace() -> str:
        """Get the Object Storage namespace for the tenancy."""
        try:
            object_storage_client = clients.object_storage
            response = object_storage_client.get_namespace()
            
            namespace = response.data
            
            result = OCIResponse(
                success=True,
                message="Object Storage namespace retrieved successfully",
                data={"namespace": namespace},
                namespace=namespace
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_namespace", "object_storage")
            return result.to_dict()

    @app.tool()
    async def list_buckets(
        namespace_name: str,
        compartment_id: str | None = None,
        name: str | None = None,
        name_starts_with: str | None = None,
        limit: int = 50
    ) -> str:
        """List Object Storage buckets using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            object_storage_client = clients.object_storage
            
            # Use official OCI SDK method pattern
            response = object_storage_client.list_buckets(
                namespace_name=namespace_name,
                compartment_id=compartment_id,
                name=name,
                name_starts_with=name_starts_with,
                limit=limit
            )
            
            buckets = []
            for bucket in response.data.items:
                buckets.append({
                    "name": bucket.name,
                    "compartment_id": bucket.compartment_id,
                    "time_created": bucket.time_created.isoformat() if bucket.time_created else None,
                    "created_by": bucket.created_by,
                    "namespace": bucket.namespace,
                    "approx_num_objects": bucket.approx_num_objects,
                    "approx_total_size": bucket.approx_total_size,
                    "public_access_type": bucket.public_access_type,
                    "storage_tier": bucket.storage_tier,
                    "etag": bucket.etag
                })
            
            formatted_buckets = format_for_llm(buckets, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_buckets)} Object Storage buckets",
                data=formatted_buckets,
                count=len(formatted_buckets),
                compartment_id=compartment_id,
                namespace=namespace_name
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_buckets", "object_storage")
            return result.to_dict()

    @app.tool()
    async def list_objects(
        namespace_name: str,
        bucket_name: str,
        prefix: str | None = None,
        start: str | None = None,
        end: str | None = None,
        limit: int = 50
    ) -> str:
        """List objects in an Object Storage bucket using official OCI SDK patterns."""
        try:
            object_storage_client = clients.object_storage
            
            # Use official OCI SDK method pattern
            response = object_storage_client.list_objects(
                namespace_name=namespace_name,
                bucket_name=bucket_name,
                prefix=prefix,
                start=start,
                end=end,
                limit=limit
            )
            
            objects = []
            for obj in response.data.objects:
                objects.append({
                    "name": obj.name,
                    "size": obj.size,
                    "md5": obj.md5,
                    "time_created": obj.time_created.isoformat() if obj.time_created else None,
                    "etag": obj.etag,
                    "storage_tier": obj.storage_tier
                })
            
            formatted_objects = format_for_llm(objects, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_objects)} objects in bucket {bucket_name}",
                data=formatted_objects,
                count=len(formatted_objects),
                namespace=namespace_name
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_objects", "object_storage")
            return result.to_dict()

    app.run()
