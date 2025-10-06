#!/usr/bin/env python3
"""
Optimized Functions MCP Server
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
    create_common_tools
)

def run_functions(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_functions") -> None:
    """Serve an optimized FastMCP app for functions operations."""
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

    # Functions-specific tools
        # Functions-specific tools
    @app.tool()
    async def list_applications(
        compartment_id: str | None = None,
        display_name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List Functions applications using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            functions_management_client = clients.functions_management
            
            # Use official OCI SDK method pattern
            response = functions_management_client.list_applications(
                compartment_id=compartment_id,
                display_name=display_name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            applications = []
            for app in response.data:
                applications.append({
                    "id": app.id,
                    "display_name": app.display_name,
                    "lifecycle_state": app.lifecycle_state,
                    "time_created": app.time_created.isoformat() if app.time_created else None,
                    "compartment_id": app.compartment_id,
                    "config": app.config,
                    "subnet_ids": app.subnet_ids,
                    "trace_config": {
                        "is_enabled": app.trace_config.is_enabled,
                        "domain_id": app.trace_config.domain_id
                    } if app.trace_config else None,
                    "freeform_tags": app.freeform_tags,
                    "defined_tags": app.defined_tags
                })
            
            formatted_applications = format_for_llm(applications, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_applications)} Functions applications",
                data=formatted_applications,
                count=len(formatted_applications),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_applications", "functions_management")
            return result.to_dict()

    @app.tool()
    async def get_application(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific application by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.functions
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific application by ID - Template implementation",
                data={"message": "This is a template implementation for get_application"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_application", "functions")
            return result.to_dict()

    @app.tool()
    async def list_functions(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """List functions in an application using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.functions
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="List functions in an application - Template implementation",
                data={"message": "This is a template implementation for list_functions"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_functions", "functions")
            return result.to_dict()

    @app.tool()
    async def get_function(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific function by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.functions
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific function by ID - Template implementation",
                data={"message": "This is a template implementation for get_function"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_function", "functions")
            return result.to_dict()

    app.run()
