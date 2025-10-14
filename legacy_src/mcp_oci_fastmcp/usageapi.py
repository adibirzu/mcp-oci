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
    OCIResponse,
    clients,
    create_common_tools,
    format_for_llm,
    handle_oci_error,
    validate_compartment_id,
)


def run_usageapi(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_usageapi") -> None:
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
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            usage_api_client = clients.usage_api
            
            # Set default time range if not provided
            if not time_usage_started:
                from datetime import datetime, timedelta
                # Usage API requires dates with zero time components
                start_date = (datetime.now() - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
                time_usage_started = start_date.isoformat()
            if not time_usage_ended:
                from datetime import datetime
                # Usage API requires dates with zero time components
                end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                time_usage_ended = end_date.isoformat()
            
            # Create request object
            from datetime import datetime

            from oci.usage_api.models import RequestSummarizedUsagesDetails
            
            request_details = RequestSummarizedUsagesDetails(
                tenant_id=compartment_id,  # tenant_id is the same as compartment_id for root
                time_usage_started=datetime.fromisoformat(time_usage_started.replace('Z', '+00:00')),
                time_usage_ended=datetime.fromisoformat(time_usage_ended.replace('Z', '+00:00')),
                granularity=granularity,
                group_by=group_by.split(',') if group_by else None,
                query_type="USAGE"
            )
            
            # Use official OCI SDK method pattern
            response = usage_api_client.request_summarized_usages(
                request_summarized_usages_details=request_details,
                limit=limit
            )
            
            summaries = []
            for summary in response.data.items:
                summaries.append({
                    "tenant_id": summary.tenant_id,
                    "tenant_name": summary.tenant_name,
                    "time_usage_started": summary.time_usage_started.isoformat() if summary.time_usage_started else None,
                    "time_usage_ended": summary.time_usage_ended.isoformat() if summary.time_usage_ended else None,
                    "service": summary.service,
                    "resource_name": summary.resource_name,
                    "resource_id": summary.resource_id,
                    "sku_part_number": summary.sku_part_number,
                    "sku_name": summary.sku_name,
                    "computed_amount": summary.computed_amount,
                    "computed_quantity": summary.computed_quantity,
                    "unit": summary.unit,
                    "unit_price": summary.unit_price,
                    "currency": summary.currency,
                    "compartment_id": summary.compartment_id,
                    "compartment_name": summary.compartment_name,
                    "compartment_path": summary.compartment_path,
                    "region": summary.region,
                    "platform": summary.platform,
                    "tags": summary.tags
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
        time_usage_started: str | None = None,
        time_usage_ended: str | None = None,
        granularity: str = "DAILY",
        limit: int = 50
    ) -> str:
        """Get specific usage summary by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
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
        limit: int = 50
    ) -> str:
        """List cost analysis queries using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
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
        limit: int = 50
    ) -> str:
        """Get specific cost analysis query using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
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
