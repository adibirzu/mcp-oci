#!/usr/bin/env python3
"""
Optimized Monitoring MCP Server
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

def run_monitoring(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-monitoring-optimized") -> None:
    """Serve an optimized FastMCP app for monitoring operations."""
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

    # Monitoring-specific tools
    @app.tool()
    async def list_metrics(
        compartment_id: str | None = None,
        name: str | None = None,
        namespace: str | None = None,
        resource_group: str | None = None,
        limit: int = 50
    ) -> str:
        """List metrics using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            monitoring_client = clients.monitoring
            
            # Use official OCI SDK method pattern
            response = monitoring_client.list_metrics(
                compartment_id=compartment_id,
                name=name,
                namespace=namespace,
                resource_group=resource_group,
                limit=limit
            )
            
            metrics = []
            for metric in response.data:
                metrics.append({
                    "name": metric.name,
                    "namespace": metric.namespace,
                    "display_name": metric.display_name,
                    "description": metric.description,
                    "resource_group": metric.resource_group,
                    "unit": metric.unit
                })
            
            formatted_metrics = format_for_llm(metrics, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_metrics)} metrics",
                data=formatted_metrics,
                count=len(formatted_metrics),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_metrics", "monitoring")
            return result.to_dict()

    @app.tool()
    async def list_alarms(
        compartment_id: str | None = None,
        display_name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List alarms using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            monitoring_client = clients.monitoring
            
            # Use official OCI SDK method pattern
            response = monitoring_client.list_alarms(
                compartment_id=compartment_id,
                display_name=display_name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            alarms = []
            for alarm in response.data:
                alarms.append({
                    "id": alarm.id,
                    "display_name": alarm.display_name,
                    "lifecycle_state": alarm.lifecycle_state,
                    "time_created": alarm.time_created.isoformat() if alarm.time_created else None,
                    "compartment_id": alarm.compartment_id,
                    "metric_compartment_id": alarm.metric_compartment_id,
                    "namespace": alarm.namespace,
                    "query": alarm.query,
                    "severity": alarm.severity,
                    "is_enabled": alarm.is_enabled
                })
            
            formatted_alarms = format_for_llm(alarms, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_alarms)} alarms",
                data=formatted_alarms,
                count=len(formatted_alarms),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_alarms", "monitoring")
            return result.to_dict()

    @app.tool()
    async def get_alarm(alarm_id: str) -> str:
        """Get a specific alarm by ID."""
        try:
            if not alarm_id.startswith("ocid1.alarm."):
                raise ValueError("Invalid alarm ID format")
            
            monitoring_client = clients.monitoring
            response = monitoring_client.get_alarm(alarm_id=alarm_id)
            
            alarm = {
                "id": response.data.id,
                "display_name": response.data.display_name,
                "lifecycle_state": response.data.lifecycle_state,
                "time_created": response.data.time_created.isoformat() if response.data.time_created else None,
                "compartment_id": response.data.compartment_id,
                "metric_compartment_id": response.data.metric_compartment_id,
                "namespace": response.data.namespace,
                "query": response.data.query,
                "severity": response.data.severity,
                "is_enabled": response.data.is_enabled
            }
            
            formatted_alarm = format_for_llm(alarm)
            
            result = OCIResponse(
                success=True,
                message="Alarm retrieved successfully",
                data=formatted_alarm,
                compartment_id=response.data.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_alarm", "monitoring")
            return result.to_dict()

    @app.tool()
    async def list_alarm_status(
        compartment_id: str | None = None,
        display_name: str | None = None,
        limit: int = 50
    ) -> str:
        """List alarm statuses using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            monitoring_client = clients.monitoring
            
            # Use official OCI SDK method pattern
            response = monitoring_client.list_alarm_status(
                compartment_id=compartment_id,
                display_name=display_name,
                limit=limit
            )
            
            alarm_statuses = []
            for status in response.data:
                alarm_statuses.append({
                    "id": status.id,
                    "display_name": status.display_name,
                    "severity": status.severity,
                    "status": status.status,
                    "suppression": status.suppression,
                    "timestamp_triggered": status.timestamp_triggered.isoformat() if status.timestamp_triggered else None
                })
            
            formatted_statuses = format_for_llm(alarm_statuses, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_statuses)} alarm statuses",
                data=formatted_statuses,
                count=len(formatted_statuses),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_alarm_status", "monitoring")
            return result.to_dict()

    @app.tool()
    async def summarize_metrics_data(
        compartment_id: str | None = None,
        namespace: str | None = None,
        resource_group: str | None = None,
        query: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        resolution: str | None = None,
        limit: int = 50
    ) -> str:
        """Summarize metrics data using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            monitoring_client = clients.monitoring
            
            # Prepare query details
            query_details = {
                "compartment_id": compartment_id
            }
            
            if namespace:
                query_details["namespace"] = namespace
            if resource_group:
                query_details["resource_group"] = resource_group
            if query:
                query_details["query"] = query
            if start_time:
                query_details["start_time"] = start_time
            if end_time:
                query_details["end_time"] = end_time
            if resolution:
                query_details["resolution"] = resolution
            
            # Use official OCI SDK method pattern
            response = monitoring_client.summarize_metrics_data(
                compartment_id=compartment_id,
                summarize_metrics_data_details=query_details
            )
            
            # Format the response data
            metrics_data = {
                "items": [],
                "summary": {
                    "total_count": len(response.data.items) if response.data.items else 0
                }
            }
            
            if response.data.items:
                for item in response.data.items[:limit]:
                    metrics_data["items"].append({
                        "namespace": item.namespace,
                        "resource_group": item.resource_group,
                        "compartment_id": item.compartment_id,
                        "name": item.name,
                        "dimensions": item.dimensions,
                        "metadata": item.metadata
                    })
            
            result = OCIResponse(
                success=True,
                message=f"Retrieved metrics data summary",
                data=metrics_data,
                count=len(metrics_data["items"]),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "summarize_metrics_data", "monitoring")
            return result.to_dict()

    app.run()
