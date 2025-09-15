#!/usr/bin/env python3
"""
Optimized Usageapi MCP Server
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

def run_usageapi(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-usageapi-optimized") -> None:
    """Serve an optimized FastMCP app for usageapi operations."""
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

    # Usageapi-specific tools
        # Usageapi-specific tools
    @app.tool()
    async def list_usage_summaries(
        compartment_id: str | None = None,
        time_usage_started: str | None = None,
        time_usage_ended: str | None = None,
        granularity: str = "DAILY",
        group_by: str | None = None,
        limit: int = 50
    ) -> str:
        """List usage summaries for cost tracking using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            usage_api_client = clients.usage_api
            
            # Set default time range if not provided
            if not time_usage_started:
                from datetime import datetime, timedelta
                time_usage_started = (datetime.now() - timedelta(days=30)).isoformat()
            if not time_usage_ended:
                from datetime import datetime
                time_usage_ended = datetime.now().isoformat()
            
            # Use official OCI SDK method pattern
            response = usage_api_client.request_usage_summaries(
                compartment_id=compartment_id,
                time_usage_started=time_usage_started,
                time_usage_ended=time_usage_ended,
                granularity=granularity,
                group_by=group_by,
                limit=limit
            )
            
            summaries = []
            for summary in response.data.items:
                summaries.append({
                    "tenant_id": summary.tenant_id,
                    "tenant_name": summary.tenant_name,
                    "time_usage_started": summary.time_usage_started.isoformat() if summary.time_usage_started else None,
                    "time_usage_ended": summary.time_usage_ended.isoformat() if summary.time_usage_ended else None,
                    "granularity": summary.granularity,
                    "is_aggregate_by_time": summary.is_aggregate_by_time,
                    "items": [
                        {
                            "service": item.service,
                            "service_name": item.service_name,
                            "resource_name": item.resource_name,
                            "resource_id": item.resource_id,
                            "sku_part_number": item.sku_part_number,
                            "sku_name": item.sku_name,
                            "usage": item.usage,
                            "unit": item.unit,
                            "compartment_id": item.compartment_id,
                            "compartment_name": item.compartment_name,
                            "compartment_path": item.compartment_path,
                            "tags": item.tags
                        } for item in summary.items
                    ]
                })
            
            formatted_summaries = format_for_llm(summaries, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_summaries)} usage summaries",
                data=formatted_summaries,
                count=len(formatted_summaries),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_usage_summaries", "usage_api")
            return result.to_dict()

    @app.tool()
    async def get_usage_summary(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific usage summary by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.usage_api
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific usage summary by ID - Template implementation",
                data={"message": "This is a template implementation for get_usage_summary"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_usage_summary", "usageapi")
            return result.to_dict()

    @app.tool()
    async def list_cost_analysis_queries(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """List cost analysis queries using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.usage_api
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="List cost analysis queries - Template implementation",
                data={"message": "This is a template implementation for list_cost_analysis_queries"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_cost_analysis_queries", "usageapi")
            return result.to_dict()

    @app.tool()
    async def get_cost_analysis_query(
        compartment_id: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> str:
        """Get specific cost analysis query using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.usage_api
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="Get specific cost analysis query - Template implementation",
                data={"message": "This is a template implementation for get_cost_analysis_query"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_cost_analysis_query", "usageapi")
            return result.to_dict()

    app.run()
