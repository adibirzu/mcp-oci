#!/usr/bin/env python3
"""
Optimized Dns MCP Server
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
    OCIResponse,
    clients,
    create_common_tools,
    handle_oci_error,
    validate_compartment_id,
)


def run_dns(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_dns") -> None:
    """Serve an optimized FastMCP app for dns operations."""
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

    # Dns-specific tools
        # Dns-specific tools
    @app.tool()
    async def list_zones(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """List DNS zones using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.dns
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="List DNS zones - Template implementation",
                data={"message": "This is a template implementation for list_zones"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_zones", "dns")
            return result.to_dict()

    @app.tool()
    async def get_zone(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific zone by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.dns
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific zone by ID - Template implementation",
                data={"message": "This is a template implementation for get_zone"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_zone", "dns")
            return result.to_dict()

    @app.tool()
    async def list_records(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """List DNS records in a zone using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.dns
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="List DNS records in a zone - Template implementation",
                data={"message": "This is a template implementation for list_records"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_records", "dns")
            return result.to_dict()

    @app.tool()
    async def get_record(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific record by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.dns
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific record by ID - Template implementation",
                data={"message": "This is a template implementation for get_record"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_record", "dns")
            return result.to_dict()

    app.run()
