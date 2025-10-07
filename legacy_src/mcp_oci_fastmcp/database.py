#!/usr/bin/env python3
"""
Optimized Database MCP Server
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
    handle_oci_error,
    validate_compartment_id,
)


def run_database(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_database") -> None:
    """Serve an optimized FastMCP app for database operations."""
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

    # Database-specific tools
    @app.tool()
    async def list_autonomous_databases(
        compartment_id: str | None = None,
        display_name: str | None = None,
        db_version: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List Autonomous Databases using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            database_client = clients.database
            
            # Use official OCI SDK method pattern
            response = database_client.list_autonomous_databases(
                compartment_id=compartment_id,
                display_name=display_name,
                db_version=db_version,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            databases = []
            for db in response.data:
                databases.append({
                    "id": db.id,
                    "display_name": db.display_name,
                    "db_version": db.db_version,
                    "lifecycle_state": db.lifecycle_state,
                    "time_created": db.time_created.isoformat() if db.time_created else None,
                    "compartment_id": db.compartment_id,
                    "cpu_core_count": db.cpu_core_count,
                    "data_storage_size_in_tbs": db.data_storage_size_in_tbs,
                    "db_workload": db.db_workload,
                    "is_free_tier": db.is_free_tier
                })
            
            formatted_databases = format_for_llm(databases, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_databases)} Autonomous Databases",
                data=formatted_databases,
                count=len(formatted_databases),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_autonomous_databases", "database")
            return result.to_dict()

    @app.tool()
    async def get_autonomous_database(autonomous_database_id: str) -> str:
        """Get a specific Autonomous Database by ID."""
        try:
            if not autonomous_database_id.startswith("ocid1.autonomousdatabase."):
                raise ValueError("Invalid Autonomous Database ID format")
            
            database_client = clients.database
            response = database_client.get_autonomous_database(autonomous_database_id=autonomous_database_id)
            
            db = {
                "id": response.data.id,
                "display_name": response.data.display_name,
                "db_version": response.data.db_version,
                "lifecycle_state": response.data.lifecycle_state,
                "time_created": response.data.time_created.isoformat() if response.data.time_created else None,
                "compartment_id": response.data.compartment_id,
                "cpu_core_count": response.data.cpu_core_count,
                "data_storage_size_in_tbs": response.data.data_storage_size_in_tbs,
                "db_workload": response.data.db_workload,
                "is_free_tier": response.data.is_free_tier
            }
            
            formatted_db = format_for_llm(db)
            
            result = OCIResponse(
                success=True,
                message="Autonomous Database retrieved successfully",
                data=formatted_db,
                compartment_id=response.data.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_autonomous_database", "database")
            return result.to_dict()

    @app.tool()
    async def list_db_systems(
        compartment_id: str | None = None,
        display_name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List DB Systems using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            database_client = clients.database
            
            # Use official OCI SDK method pattern
            response = database_client.list_db_systems(
                compartment_id=compartment_id,
                display_name=display_name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            db_systems = []
            for dbs in response.data:
                db_systems.append({
                    "id": dbs.id,
                    "display_name": dbs.display_name,
                    "lifecycle_state": dbs.lifecycle_state,
                    "time_created": dbs.time_created.isoformat() if dbs.time_created else None,
                    "compartment_id": dbs.compartment_id,
                    "availability_domain": dbs.availability_domain,
                    "shape": dbs.shape,
                    "cpu_core_count": dbs.cpu_core_count,
                    "database_edition": dbs.database_edition
                })
            
            formatted_db_systems = format_for_llm(db_systems, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_db_systems)} DB Systems",
                data=formatted_db_systems,
                count=len(formatted_db_systems),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_db_systems", "database")
            return result.to_dict()

    @app.tool()
    async def get_db_system(db_system_id: str) -> str:
        """Get a specific DB System by ID."""
        try:
            if not db_system_id.startswith("ocid1.dbsystem."):
                raise ValueError("Invalid DB System ID format")
            
            database_client = clients.database
            response = database_client.get_db_system(db_system_id=db_system_id)
            
            dbs = {
                "id": response.data.id,
                "display_name": response.data.display_name,
                "lifecycle_state": response.data.lifecycle_state,
                "time_created": response.data.time_created.isoformat() if response.data.time_created else None,
                "compartment_id": response.data.compartment_id,
                "availability_domain": response.data.availability_domain,
                "shape": response.data.shape,
                "cpu_core_count": response.data.cpu_core_count,
                "database_edition": response.data.database_edition
            }
            
            formatted_dbs = format_for_llm(dbs)
            
            result = OCIResponse(
                success=True,
                message="DB System retrieved successfully",
                data=formatted_dbs,
                compartment_id=response.data.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_db_system", "database")
            return result.to_dict()

    @app.tool()
    async def list_database_software_images(
        compartment_id: str | None = None,
        display_name: str | None = None,
        image_shape_family: str | None = None,
        limit: int = 50
    ) -> str:
        """List Database Software Images using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            database_client = clients.database
            
            # Use official OCI SDK method pattern
            response = database_client.list_database_software_images(
                compartment_id=compartment_id,
                display_name=display_name,
                image_shape_family=image_shape_family,
                limit=limit
            )
            
            images = []
            for img in response.data:
                images.append({
                    "id": img.id,
                    "display_name": img.display_name,
                    "lifecycle_state": img.lifecycle_state,
                    "time_created": img.time_created.isoformat() if img.time_created else None,
                    "compartment_id": img.compartment_id,
                    "image_shape_family": img.image_shape_family,
                    "database_version": img.database_version
                })
            
            formatted_images = format_for_llm(images, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_images)} Database Software Images",
                data=formatted_images,
                count=len(formatted_images),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_database_software_images", "database")
            return result.to_dict()

    app.run()
