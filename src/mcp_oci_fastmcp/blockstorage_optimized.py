#!/usr/bin/env python3
"""
Optimized Blockstorage MCP Server
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

def run_blockstorage(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-blockstorage-optimized") -> None:
    """Serve an optimized FastMCP app for blockstorage operations."""
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

    # Blockstorage-specific tools
        # Blockstorage-specific tools
    @app.tool()
    async def list_volumes(
        compartment_id: str | None = None,
        availability_domain: str | None = None,
        display_name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List block storage volumes using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            block_storage_client = clients.block_storage
            
            # Use official OCI SDK method pattern
            response = block_storage_client.list_volumes(
                compartment_id=compartment_id,
                availability_domain=availability_domain,
                display_name=display_name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            volumes = []
            for volume in response.data:
                volumes.append({
                    "id": volume.id,
                    "display_name": volume.display_name,
                    "lifecycle_state": volume.lifecycle_state,
                    "availability_domain": volume.availability_domain,
                    "time_created": volume.time_created.isoformat() if volume.time_created else None,
                    "compartment_id": volume.compartment_id,
                    "size_in_gbs": volume.size_in_gbs,
                    "size_in_mbs": volume.size_in_mbs,
                    "vpus_per_gb": volume.vpus_per_gb,
                    "volume_group_id": volume.volume_group_id,
                    "is_auto_tune_enabled": volume.is_auto_tune_enabled,
                    "is_hydrated": volume.is_hydrated,
                    "kms_key_id": volume.kms_key_id,
                    "volume_tags": volume.volume_tags
                })
            
            formatted_volumes = format_for_llm(volumes, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_volumes)} block volumes",
                data=formatted_volumes,
                count=len(formatted_volumes),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_volumes", "block_storage")
            return result.to_dict()

    @app.tool()
    async def get_volume(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific volume by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.block_storage
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific volume by ID - Template implementation",
                data={"message": "This is a template implementation for get_volume"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_volume", "blockstorage")
            return result.to_dict()

    @app.tool()
    async def list_volume_backups(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """List volume backups using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.block_storage
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="List volume backups - Template implementation",
                data={"message": "This is a template implementation for list_volume_backups"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_volume_backups", "blockstorage")
            return result.to_dict()

    @app.tool()
    async def get_volume_backup(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific volume backup by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.block_storage
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific volume backup by ID - Template implementation",
                data={"message": "This is a template implementation for get_volume_backup"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_volume_backup", "blockstorage")
            return result.to_dict()

    app.run()
