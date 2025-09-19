#!/usr/bin/env python3
"""
Optimized Log Analytics MCP Server
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
    get_log_analytics_namespace,
    handle_oci_error,
    validate_compartment_id,
)


def run_loganalytics(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_loganalytics") -> None:
    """Serve an optimized FastMCP app for Log Analytics operations."""
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

    # Log Analytics-specific tools
    @app.tool()
    async def list_sources(
        compartment_id: str | None = None,
        display_name: str | None = None,
        is_system: bool | None = None,
        limit: int = 50
    ) -> str:
        """List Log Analytics sources using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Auto-discover namespace
            namespace = get_log_analytics_namespace()
            
            log_analytics_client = clients.log_analytics
            
            # Use official OCI SDK method pattern
            response = log_analytics_client.list_sources(
                namespace_name=namespace,
                compartment_id=compartment_id,
                display_name=display_name,
                is_system=is_system,
                limit=limit
            )
            
            sources = []
            for source in response.data.items:
                sources.append({
                    "id": source.id,
                    "display_name": source.display_name,
                    "description": source.description,
                    "is_system": source.is_system,
                    "source_type": source.source_type,
                    "time_created": source.time_created.isoformat() if source.time_created else None,
                    "time_updated": source.time_updated.isoformat() if source.time_updated else None,
                    "status": source.status
                })
            
            formatted_sources = format_for_llm(sources, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_sources)} Log Analytics sources",
                data=formatted_sources,
                count=len(formatted_sources),
                compartment_id=compartment_id,
                namespace=namespace
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_sources", "log_analytics")
            return result.to_dict()

    @app.tool()
    async def list_log_groups(
        compartment_id: str | None = None,
        display_name: str | None = None,
        limit: int = 50
    ) -> str:
        """List Log Analytics log groups using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Auto-discover namespace
            namespace = get_log_analytics_namespace()
            
            log_analytics_client = clients.log_analytics
            
            # Use official OCI SDK method pattern
            response = log_analytics_client.list_log_groups(
                namespace_name=namespace,
                compartment_id=compartment_id,
                display_name=display_name,
                limit=limit
            )
            
            groups = []
            for group in response.data.items:
                groups.append({
                    "id": group.id,
                    "display_name": group.display_name,
                    "description": group.description,
                    "compartment_id": group.compartment_id,
                    "time_created": group.time_created.isoformat() if group.time_created else None,
                    "time_updated": group.time_updated.isoformat() if group.time_updated else None,
                    "lifecycle_state": group.lifecycle_state
                })
            
            formatted_groups = format_for_llm(groups, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_groups)} Log Analytics log groups",
                data=formatted_groups,
                count=len(formatted_groups),
                compartment_id=compartment_id,
                namespace=namespace
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_log_groups", "log_analytics")
            return result.to_dict()

    @app.tool()
    async def list_entities(
        compartment_id: str | None = None,
        display_name: str | None = None,
        entity_type: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List Log Analytics entities using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Auto-discover namespace
            namespace = get_log_analytics_namespace()
            
            log_analytics_client = clients.log_analytics
            
            # Use official OCI SDK method pattern
            response = log_analytics_client.list_log_analytics_entities(
                namespace_name=namespace,
                compartment_id=compartment_id,
                display_name=display_name,
                entity_type=entity_type,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            entities = []
            for entity in response.data.items:
                entities.append({
                    "id": entity.id,
                    "display_name": entity.display_name,
                    "entity_type_name": entity.entity_type_name,
                    "compartment_id": entity.compartment_id,
                    "lifecycle_state": entity.lifecycle_state,
                    "time_created": entity.time_created.isoformat() if entity.time_created else None,
                    "time_updated": entity.time_updated.isoformat() if entity.time_updated else None,
                    "hostname": entity.hostname
                })
            
            formatted_entities = format_for_llm(entities, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_entities)} Log Analytics entities",
                data=formatted_entities,
                count=len(formatted_entities),
                compartment_id=compartment_id,
                namespace=namespace
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_entities", "log_analytics")
            return result.to_dict()

    @app.tool()
    async def run_query(
        query_string: str,
        time_start: str,
        time_end: str,
        compartment_id: str | None = None,
        subsystem: str | None = None,
        max_total_count: int | None = None,
        limit: int = 50
    ) -> str:
        """Run a Log Analytics query using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Auto-discover namespace
            namespace = get_log_analytics_namespace()
            
            log_analytics_client = clients.log_analytics
            
            # Prepare query details using correct SDK model
            time_filter = oci.log_analytics.models.TimeRange(
                time_start=datetime.fromisoformat(time_start),
                time_end=datetime.fromisoformat(time_end),
            )
            query_details = oci.log_analytics.models.QueryDetails(
                compartment_id=compartment_id,
                query_string=query_string,
                sub_system=(subsystem or oci.log_analytics.models.QueryDetails.SUB_SYSTEM_LOG),
                max_total_count=max_total_count or limit,
                time_filter=time_filter,
                should_include_columns=True,
                should_include_fields=False,
                should_include_total_count=True,
            )

            # Use official OCI SDK method pattern
            response = log_analytics_client.query(
                namespace_name=namespace,
                query_details=query_details,
                limit=limit,
            )
            
            # Format query results
            data = response.data
            query_result = {
                "query_job_id": getattr(data, 'query_job_id', None),
                "query_status": getattr(data, 'query_status', None),
                "results": getattr(data, 'results', []) or [],
                "columns": getattr(data, 'columns', []) or [],
                "total_count": getattr(data, 'total_count', None),
                "next_page": getattr(response, 'opc_next_page', None)
            }
            
            result = OCIResponse(
                success=True,
                message="Query executed successfully",
                data=query_result,
                compartment_id=compartment_id,
                namespace=namespace
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "run_query", "log_analytics")
            return result.to_dict()

    @app.tool()
    async def get_namespace() -> str:
        """Get the Log Analytics namespace for the tenancy."""
        try:
            namespace = get_log_analytics_namespace()
            
            result = OCIResponse(
                success=True,
                message="Log Analytics namespace retrieved successfully",
                data={"namespace": namespace},
                namespace=namespace
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_namespace", "log_analytics")
            return result.to_dict()

    app.run()
