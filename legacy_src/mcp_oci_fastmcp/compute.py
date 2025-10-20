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
    OCIResponse,
    clients,
    create_common_tools,
    format_for_llm,
    get_all_compartments_recursive,
    handle_oci_error,
    validate_compartment_id,
)


def run_compute(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_compute") -> None:
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
        limit: int = 50,
        search_all_compartments: bool = True
    ) -> str:
        """List compute instances using official OCI SDK patterns. Searches all accessible compartments by default."""
        try:
            compute_client = clients.compute
            identity_client = clients.identity
            
            instances = []
            
            if compartment_id is None or search_all_compartments:
                # Search all accessible compartments using recursive discovery
                if compartment_id is None:
                    # Get ALL compartments recursively (including sub-compartments)
                    compartments = get_all_compartments_recursive(identity_client, clients.root_compartment_id)
                else:
                    # Search specific compartment and its children recursively
                    if not validate_compartment_id(compartment_id):
                        raise ValueError("Invalid compartment ID format")
                    
                    compartments = get_all_compartments_recursive(identity_client, compartment_id)
                
                # Search each compartment for instances
                for comp in compartments:
                    try:
                        comp_response = compute_client.list_instances(
                            compartment_id=comp.id,
                            availability_domain=availability_domain,
                            display_name=display_name,
                            lifecycle_state=lifecycle_state,
                            limit=1000  # Use higher limit for individual compartment searches
                        )
                        
                        for instance in comp_response.data:
                            instances.append({
                                "id": instance.id,
                                "display_name": instance.display_name,
                                "lifecycle_state": instance.lifecycle_state,
                                "availability_domain": instance.availability_domain,
                                "shape": instance.shape,
                                "time_created": instance.time_created.isoformat() if instance.time_created else None,
                                "compartment_id": instance.compartment_id,
                                "compartment_name": comp.name,
                                "region": instance.region
                            })
                    except Exception:
                        # Skip compartments with errors (e.g., no permissions)
                        continue
            else:
                # Search specific compartment only
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
                
                response = compute_client.list_instances(
                    compartment_id=compartment_id,
                    availability_domain=availability_domain,
                    display_name=display_name,
                    lifecycle_state=lifecycle_state,
                    limit=limit
                )
                
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
            
            # Apply limit to final results
            if limit and len(instances) > limit:
                instances = instances[:limit]
            
            formatted_instances = format_for_llm(instances, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_instances)} compute instances across all accessible compartments (including sub-compartments)",
                data=formatted_instances,
                count=len(formatted_instances),
                compartment_id=compartment_id or "all_accessible_recursive"
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
        """List stopped compute instances across all accessible compartments."""
        try:
            # Use the enhanced list_instances function with lifecycle_state filter
            return await list_instances(
                compartment_id=compartment_id,
                lifecycle_state="STOPPED",
                limit=limit,
                search_all_compartments=True
            )
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
            elif not validate_compartment_id(compartment_id):
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

    @app.tool()
    async def start_instance(instance_id: str) -> str:
        """Start a compute instance."""
        try:
            if not instance_id.startswith("ocid1.instance."):
                raise ValueError("Invalid instance ID format")
            
            compute_client = clients.compute
            
            # Start the instance
            response = compute_client.instance_action(
                instance_id=instance_id,
                action="START"
            )
            
            result = OCIResponse(
                success=True,
                message=f"Instance {instance_id} start request submitted successfully",
                data={
                    "instance_id": instance_id,
                    "action": "START",
                    "status": "SUBMITTED"
                },
                compartment_id=response.data.compartment_id if hasattr(response, 'data') else None
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "start_instance", "compute")
            return result.to_dict()

    @app.tool()
    async def stop_instance(instance_id: str, force: bool = False) -> str:
        """Stop a compute instance."""
        try:
            if not instance_id.startswith("ocid1.instance."):
                raise ValueError("Invalid instance ID format")
            
            compute_client = clients.compute
            
            # Stop the instance
            action = "FORCESTOP" if force else "STOP"
            response = compute_client.instance_action(
                instance_id=instance_id,
                action=action
            )
            
            result = OCIResponse(
                success=True,
                message=f"Instance {instance_id} {action.lower()} request submitted successfully",
                data={
                    "instance_id": instance_id,
                    "action": action,
                    "status": "SUBMITTED"
                },
                compartment_id=response.data.compartment_id if hasattr(response, 'data') else None
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "stop_instance", "compute")
            return result.to_dict()

    @app.tool()
    async def restart_instance(instance_id: str, force: bool = False) -> str:
        """Restart a compute instance."""
        try:
            if not instance_id.startswith("ocid1.instance."):
                raise ValueError("Invalid instance ID format")
            
            compute_client = clients.compute
            
            # Restart the instance
            action = "FORCERESET" if force else "RESET"
            response = compute_client.instance_action(
                instance_id=instance_id,
                action=action
            )
            
            result = OCIResponse(
                success=True,
                message=f"Instance {instance_id} {action.lower()} request submitted successfully",
                data={
                    "instance_id": instance_id,
                    "action": action,
                    "status": "SUBMITTED"
                },
                compartment_id=response.data.compartment_id if hasattr(response, 'data') else None
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "restart_instance", "compute")
            return result.to_dict()

    @app.tool()
    async def get_instance_details(instance_id: str) -> str:
        """Get detailed information about a specific instance."""
        try:
            if not instance_id.startswith("ocid1.instance."):
                raise ValueError("Invalid instance ID format")
            
            compute_client = clients.compute
            response = compute_client.get_instance(instance_id=instance_id)
            
            instance = response.data
            instance_details = {
                "id": instance.id,
                "display_name": instance.display_name,
                "lifecycle_state": instance.lifecycle_state,
                "availability_domain": instance.availability_domain,
                "shape": instance.shape,
                "time_created": instance.time_created.isoformat() if instance.time_created else None,
                "compartment_id": instance.compartment_id,
                "region": instance.region,
                "fault_domain": instance.fault_domain,
                "image_id": instance.image_id,
                "extended_metadata": instance.extended_metadata,
                "metadata": instance.metadata,
                "source_details": {
                    "source_type": instance.source_details.source_type,
                    "image_id": instance.source_details.image_id,
                    "boot_volume_size_in_gbs": getattr(instance.source_details, 'boot_volume_size_in_gbs', None)
                } if instance.source_details else None,
                "shape_config": {
                    "ocpus": instance.shape_config.ocpus,
                    "memory_in_gbs": instance.shape_config.memory_in_gbs,
                    "baseline_ocpu_utilization": instance.shape_config.baseline_ocpu_utilization
                } if instance.shape_config else None
            }
            
            result = OCIResponse(
                success=True,
                message=f"Retrieved details for instance {instance.display_name}",
                data=instance_details,
                compartment_id=instance.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_instance_details", "compute")
            return result.to_dict()

    app.run()
