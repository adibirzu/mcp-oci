#!/usr/bin/env python3
"""
Optimized Loadbalancer MCP Server
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


def run_loadbalancer(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_loadbalancer") -> None:
    """Serve an optimized FastMCP app for loadbalancer operations."""
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

    # Loadbalancer-specific tools
        # Loadbalancer-specific tools
    @app.tool()
    async def list_load_balancers(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """List load balancers using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.loadbalancer
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="List load balancers - Template implementation",
                data={"message": "This is a template implementation for list_load_balancers"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_load_balancers", "loadbalancer")
            return result.to_dict()

    @app.tool()
    async def get_load_balancer(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific load balancer by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.loadbalancer
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific load balancer by ID - Template implementation",
                data={"message": "This is a template implementation for get_load_balancer"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_load_balancer", "loadbalancer")
            return result.to_dict()

    @app.tool()
    async def list_backend_sets(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """List backend sets using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.loadbalancer
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="List backend sets - Template implementation",
                data={"message": "This is a template implementation for list_backend_sets"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_backend_sets", "loadbalancer")
            return result.to_dict()

    @app.tool()
    async def get_backend_set(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific backend set by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.loadbalancer
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific backend set by ID - Template implementation",
                data={"message": "This is a template implementation for get_backend_set"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_backend_set", "loadbalancer")
            return result.to_dict()

    app.run()
