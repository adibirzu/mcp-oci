#!/usr/bin/env python3
"""
Optimized Compute MCP Server
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

def run_compute(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-compute-optimized") -> None:
    """Serve an optimized FastMCP app for compute operations."""
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

    # Compute-specific tools
    @app.tool()
    async def list_instances(
        compartment_id: str | None = None,
        availability_domain: str | None = None,
        display_name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List compute instances using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            compute_client = clients.compute
            
            # Use official OCI SDK method pattern
            response = compute_client.list_instances(
                compartment_id=compartment_id,
                availability_domain=availability_domain,
                display_name=display_name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            instances = []
            for instance in response.data:
                instances.append({
                    "id": instance.id,
                    "display_name": instance.display_name,
                    "lifecycle_state": instance.lifecycle_state,
                    "availability_domain": instance.availability_domain,
                    "shape": instance.shape,
                    "time_created": instance.time_created.isoformat() if instance.time_created else None,
                    "compartment_id": instance.compartment_id,
                    "region": instance.region
                })
            
            formatted_instances = format_for_llm(instances, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_instances)} compute instances",
                data=formatted_instances,
                count=len(formatted_instances),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_instances", "compute")
            return result.to_dict()

    @app.tool()
    async def get_instance(instance_id: str) -> str:
        """Get a specific compute instance by ID."""
        try:
            if not instance_id.startswith("ocid1.instance."):
                raise ValueError("Invalid instance ID format")
            
            compute_client = clients.compute
            response = compute_client.get_instance(instance_id=instance_id)
            
            instance = {
                "id": response.data.id,
                "display_name": response.data.display_name,
                "lifecycle_state": response.data.lifecycle_state,
                "availability_domain": response.data.availability_domain,
                "shape": response.data.shape,
                "time_created": response.data.time_created.isoformat() if response.data.time_created else None,
                "compartment_id": response.data.compartment_id,
                "region": response.data.region,
                "image_id": response.data.image_id,
                "fault_domain": response.data.fault_domain
            }
            
            formatted_instance = format_for_llm(instance)
            
            result = OCIResponse(
                success=True,
                message="Instance retrieved successfully",
                data=formatted_instance,
                compartment_id=response.data.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_instance", "compute")
            return result.to_dict()

    @app.tool()
    async def list_stopped_instances(
        compartment_id: str | None = None,
        limit: int = 50
    ) -> str:
        """List stopped compute instances."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            compute_client = clients.compute
            
            # Use official OCI SDK method pattern
            response = compute_client.list_instances(
                compartment_id=compartment_id,
                lifecycle_state="STOPPED",
                limit=limit
            )
            
            instances = []
            for instance in response.data:
                instances.append({
                    "id": instance.id,
                    "display_name": instance.display_name,
                    "lifecycle_state": instance.lifecycle_state,
                    "availability_domain": instance.availability_domain,
                    "shape": instance.shape,
                    "time_created": instance.time_created.isoformat() if instance.time_created else None,
                    "compartment_id": instance.compartment_id,
                    "region": instance.region
                })
            
            formatted_instances = format_for_llm(instances, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_instances)} stopped instances",
                data=formatted_instances,
                count=len(formatted_instances),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_stopped_instances", "compute")
            return result.to_dict()

    @app.tool()
    async def search_instances(
        compartment_id: str | None = None,
        query: str | None = None,
        limit: int = 50
    ) -> str:
        """Search for compute instances using OCI Resource Search API."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # For now, fall back to list_instances with display_name filter
            # In a full implementation, you would use the Resource Search API
            compute_client = clients.compute
            
            search_params = {
                "compartment_id": compartment_id,
                "limit": limit
            }
            
            if query:
                search_params["display_name"] = query
            
            response = compute_client.list_instances(**search_params)
            
            instances = []
            for instance in response.data:
                instances.append({
                    "id": instance.id,
                    "display_name": instance.display_name,
                    "lifecycle_state": instance.lifecycle_state,
                    "availability_domain": instance.availability_domain,
                    "shape": instance.shape,
                    "time_created": instance.time_created.isoformat() if instance.time_created else None,
                    "compartment_id": instance.compartment_id,
                    "region": instance.region
                })
            
            formatted_instances = format_for_llm(instances, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_instances)} instances matching search criteria",
                data=formatted_instances,
                count=len(formatted_instances),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "search_instances", "compute")
            return result.to_dict()

    app.run()
