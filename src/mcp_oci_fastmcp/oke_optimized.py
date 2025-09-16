#!/usr/bin/env python3
"""
Optimized Oke MCP Server
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

def run_oke(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_oke") -> None:
    """Serve an optimized FastMCP app for oke operations."""
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

    # Oke-specific tools
        # Oke-specific tools
    @app.tool()
    async def list_clusters(
        compartment_id: str | None = None,
        display_name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List OKE clusters using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            container_engine_client = clients.container_engine
            
            # Use official OCI SDK method pattern
            response = container_engine_client.list_clusters(
                compartment_id=compartment_id,
                display_name=display_name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            clusters = []
            for cluster in response.data:
                clusters.append({
                    "id": cluster.id,
                    "display_name": cluster.display_name,
                    "lifecycle_state": cluster.lifecycle_state,
                    "time_created": cluster.time_created.isoformat() if cluster.time_created else None,
                    "compartment_id": cluster.compartment_id,
                    "kubernetes_version": cluster.kubernetes_version,
                    "vcn_id": cluster.vcn_id,
                    "endpoint_config": {
                        "is_public_ip_enabled": cluster.endpoint_config.is_public_ip_enabled,
                        "subnet_id": cluster.endpoint_config.subnet_id,
                        "nsg_ids": cluster.endpoint_config.nsg_ids
                    } if cluster.endpoint_config else None,
                    "node_pools": [
                        {
                            "id": np.id,
                            "display_name": np.display_name,
                            "lifecycle_state": np.lifecycle_state,
                            "node_image_id": np.node_image_id,
                            "node_shape": np.node_shape,
                            "node_shape_config": {
                                "ocpus": np.node_shape_config.ocpus,
                                "memory_in_gbs": np.node_shape_config.memory_in_gbs
                            } if np.node_shape_config else None,
                            "node_count": np.node_count,
                            "initial_node_labels": np.initial_node_labels,
                            "ssh_public_key": np.ssh_public_key
                        } for np in cluster.node_pools
                    ] if cluster.node_pools else []
                })
            
            formatted_clusters = format_for_llm(clusters, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_clusters)} OKE clusters",
                data=formatted_clusters,
                count=len(formatted_clusters),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_clusters", "container_engine")
            return result.to_dict()

    @app.tool()
    async def get_cluster(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific cluster by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.oke
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific cluster by ID - Template implementation",
                data={"message": "This is a template implementation for get_cluster"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_cluster", "oke")
            return result.to_dict()

    @app.tool()
    async def list_node_pools(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """List node pools using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.oke
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="List node pools - Template implementation",
                data={"message": "This is a template implementation for list_node_pools"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_node_pools", "oke")
            return result.to_dict()

    @app.tool()
    async def get_node_pool(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific node pool by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.oke
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific node pool by ID - Template implementation",
                data={"message": "This is a template implementation for get_node_pool"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_node_pool", "oke")
            return result.to_dict()

    app.run()
