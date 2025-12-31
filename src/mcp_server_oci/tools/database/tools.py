"""
OCI Database domain tool implementations.
"""
from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from ...core.client import get_oci_client
from ...core.errors import format_error_response, handle_oci_error
from ...core.models import ResponseFormat
from ...core.observability import observe_tool
from .formatters import DatabaseFormatter
from .models import (
    GetAutonomousDatabaseInput,
    GetDatabaseMetricsInput,
    ListAutonomousDatabasesInput,
    ListBackupsInput,
    ListDBSystemsInput,
    StartAutonomousDatabaseInput,
    StopAutonomousDatabaseInput,
)


def register_database_tools(mcp: FastMCP) -> None:
    """Register all database domain tools with the MCP server."""

    @mcp.tool(
        name="oci_database_list_autonomous",
        annotations={
            "title": "List Autonomous Databases",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def list_autonomous_databases(params: ListAutonomousDatabasesInput, ctx: Context) -> str:
        """List Autonomous Databases in a compartment.

        Retrieves all Autonomous Databases (ATP, ADW, AJD, APEX) in the specified
        compartment with optional filtering by workload type and lifecycle state.

        Args:
            params: ListAutonomousDatabasesInput with compartment_id and filters

        Returns:
            List of Autonomous Databases in requested format (markdown or json)

        Example:
            {"compartment_id": "ocid1.compartment...", "workload_type": "OLTP", "limit": 20}
        """
        async with observe_tool("oci_database_list_autonomous", "database", params.model_dump()):
            await ctx.report_progress(0.1, "Connecting to OCI Database service...")

            try:
                async with get_oci_client() as client:
                    db_client = client.database

                    await ctx.report_progress(0.3, "Fetching Autonomous Databases...")

                    # Build request kwargs
                    kwargs: dict[str, Any] = {
                        "compartment_id": params.compartment_id,
                        "limit": params.limit,
                    }

                    if params.workload_type:
                        kwargs["db_workload"] = params.workload_type.value
                    if params.lifecycle_state:
                        kwargs["lifecycle_state"] = params.lifecycle_state.value
                    if params.display_name:
                        kwargs["display_name"] = params.display_name

                    response = await asyncio.to_thread(
                        db_client.list_autonomous_databases,
                        **kwargs
                    )

                    await ctx.report_progress(0.7, "Processing results...")

                    items = response.data if response.data else []

                    # Apply offset manually (OCI API doesn't support offset)
                    all_items = items
                    items = items[params.offset:params.offset + params.limit]

                    # Convert to dicts
                    items_data = [_adb_to_dict(db) for db in items]
                    has_more = params.offset + len(items_data) < len(all_items)
                    next_off = params.offset + len(items_data) if has_more else None

                    result = {
                        "total": len(all_items),
                        "count": len(items_data),
                        "offset": params.offset,
                        "items": items_data,
                        "has_more": has_more,
                        "next_offset": next_off
                    }

                    await ctx.report_progress(0.9, "Formatting output...")

                    if params.response_format == ResponseFormat.JSON:
                        return DatabaseFormatter.to_json(result)
                    return DatabaseFormatter.autonomous_list_markdown(result)

            except Exception as e:
                error = handle_oci_error(e, "listing Autonomous Databases")
                return format_error_response(error, params.response_format.value)


    @mcp.tool(
        name="oci_database_get_autonomous",
        annotations={
            "title": "Get Autonomous Database Details",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def get_autonomous_database(params: GetAutonomousDatabaseInput, ctx: Context) -> str:
        """Get detailed information about a specific Autonomous Database.

        Retrieves complete details including configuration, connection strings,
        and current state for an Autonomous Database.

        Args:
            params: GetAutonomousDatabaseInput with database_id

        Returns:
            Detailed Autonomous Database information

        Example:
            {"database_id": "ocid1.autonomousdatabase.oc1..."}
        """
        async with observe_tool("oci_database_get_autonomous", "database", params.model_dump()):
            await ctx.report_progress(0.1, "Fetching Autonomous Database details...")

            try:
                async with get_oci_client() as client:
                    db_client = client.database

                    response = await asyncio.to_thread(
                        db_client.get_autonomous_database,
                        autonomous_database_id=params.database_id
                    )

                    await ctx.report_progress(0.8, "Formatting output...")

                    db_data = _adb_to_dict(response.data, include_connection=True)

                    if params.response_format == ResponseFormat.JSON:
                        return DatabaseFormatter.to_json(db_data)
                    return DatabaseFormatter.autonomous_detail_markdown(db_data)

            except Exception as e:
                error = handle_oci_error(e, "getting Autonomous Database")
                return format_error_response(error, params.response_format.value)


    @mcp.tool(
        name="oci_database_start_autonomous",
        annotations={
            "title": "Start Autonomous Database",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def start_autonomous_database(params: StartAutonomousDatabaseInput, ctx: Context) -> str:
        """Start a stopped Autonomous Database.

        Initiates the start operation for a stopped Autonomous Database.
        Can optionally wait for the database to reach AVAILABLE state.

        Args:
            params: StartAutonomousDatabaseInput with database_id

        Returns:
            Result of the start operation

        Example:
            {"database_id": "ocid1.autonomousdatabase.oc1...", "wait_for_state": true}
        """
        # Check if mutations are allowed
        if os.getenv("ALLOW_MUTATIONS", "").lower() != "true":
            return (
                "❌ **Error:** Database mutations are disabled. "
                "Set ALLOW_MUTATIONS=true to enable."
            )

        async with observe_tool("oci_database_start_autonomous", "database", params.model_dump()):
            await ctx.report_progress(0.1, "Starting Autonomous Database...")

            try:
                async with get_oci_client() as client:
                    db_client = client.database

                    # Get current state first
                    current = await asyncio.to_thread(
                        db_client.get_autonomous_database,
                        autonomous_database_id=params.database_id
                    )

                    if current.data.lifecycle_state == "AVAILABLE":
                        db_data = _adb_to_dict(current.data)
                        return DatabaseFormatter.action_result_markdown(
                            "start", db_data, True, "Database is already running."
                        )

                    if current.data.lifecycle_state not in ("STOPPED", "UNAVAILABLE"):
                        db_data = _adb_to_dict(current.data)
                        return DatabaseFormatter.action_result_markdown(
                            "start", db_data, False,
                            f"Cannot start database in state: {current.data.lifecycle_state}"
                        )

                    await ctx.report_progress(0.3, "Sending start request...")

                    response = await asyncio.to_thread(
                        db_client.start_autonomous_database,
                        autonomous_database_id=params.database_id
                    )

                    db_data = _adb_to_dict(response.data)

                    if params.wait_for_state:
                        await ctx.report_progress(0.5, "Waiting for database to start...")
                        # Note: In production, use OCI waiter
                        # For now, just return the current state

                    await ctx.report_progress(0.9, "Formatting result...")

                    if params.response_format == ResponseFormat.JSON:
                        return DatabaseFormatter.to_json({"success": True, "database": db_data})
                    return DatabaseFormatter.action_result_markdown(
                        "start", db_data, True, "Start operation initiated successfully."
                    )

            except Exception as e:
                error = handle_oci_error(e, "starting Autonomous Database")
                return format_error_response(error, params.response_format.value)


    @mcp.tool(
        name="oci_database_stop_autonomous",
        annotations={
            "title": "Stop Autonomous Database",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def stop_autonomous_database(params: StopAutonomousDatabaseInput, ctx: Context) -> str:
        """Stop a running Autonomous Database.

        Initiates the stop operation for a running Autonomous Database.
        Stopped databases do not incur compute charges but retain storage.

        Args:
            params: StopAutonomousDatabaseInput with database_id

        Returns:
            Result of the stop operation

        Example:
            {"database_id": "ocid1.autonomousdatabase.oc1...", "wait_for_state": false}
        """
        if os.getenv("ALLOW_MUTATIONS", "").lower() != "true":
            return (
                "❌ **Error:** Database mutations are disabled. "
                "Set ALLOW_MUTATIONS=true to enable."
            )

        async with observe_tool("oci_database_stop_autonomous", "database", params.model_dump()):
            await ctx.report_progress(0.1, "Stopping Autonomous Database...")

            try:
                async with get_oci_client() as client:
                    db_client = client.database

                    current = await asyncio.to_thread(
                        db_client.get_autonomous_database,
                        autonomous_database_id=params.database_id
                    )

                    if current.data.lifecycle_state == "STOPPED":
                        db_data = _adb_to_dict(current.data)
                        return DatabaseFormatter.action_result_markdown(
                            "stop", db_data, True, "Database is already stopped."
                        )

                    if current.data.lifecycle_state != "AVAILABLE":
                        db_data = _adb_to_dict(current.data)
                        return DatabaseFormatter.action_result_markdown(
                            "stop", db_data, False,
                            f"Cannot stop database in state: {current.data.lifecycle_state}"
                        )

                    await ctx.report_progress(0.3, "Sending stop request...")

                    response = await asyncio.to_thread(
                        db_client.stop_autonomous_database,
                        autonomous_database_id=params.database_id
                    )

                    db_data = _adb_to_dict(response.data)

                    await ctx.report_progress(0.9, "Formatting result...")

                    if params.response_format == ResponseFormat.JSON:
                        return DatabaseFormatter.to_json({"success": True, "database": db_data})
                    return DatabaseFormatter.action_result_markdown(
                        "stop", db_data, True, "Stop operation initiated successfully."
                    )

            except Exception as e:
                error = handle_oci_error(e, "stopping Autonomous Database")
                return format_error_response(error, params.response_format.value)


    @mcp.tool(
        name="oci_database_list_dbsystems",
        annotations={
            "title": "List DB Systems",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def list_db_systems(params: ListDBSystemsInput, ctx: Context) -> str:
        """List DB Systems (BaseDB, Exadata) in a compartment.

        Retrieves all DB Systems in the specified compartment with optional
        filtering by lifecycle state and display name.

        Args:
            params: ListDBSystemsInput with compartment_id and filters

        Returns:
            List of DB Systems in requested format

        Example:
            {"compartment_id": "ocid1.compartment...", "lifecycle_state": "AVAILABLE"}
        """
        async with observe_tool("oci_database_list_dbsystems", "database", params.model_dump()):
            await ctx.report_progress(0.1, "Connecting to OCI Database service...")

            try:
                async with get_oci_client() as client:
                    db_client = client.database

                    await ctx.report_progress(0.3, "Fetching DB Systems...")

                    kwargs: dict[str, Any] = {
                        "compartment_id": params.compartment_id,
                        "limit": params.limit,
                    }

                    if params.lifecycle_state:
                        kwargs["lifecycle_state"] = params.lifecycle_state.value
                    if params.display_name:
                        kwargs["display_name"] = params.display_name

                    response = await asyncio.to_thread(
                        db_client.list_db_systems,
                        **kwargs
                    )

                    await ctx.report_progress(0.7, "Processing results...")

                    items = response.data if response.data else []
                    all_items = items
                    items = items[params.offset:params.offset + params.limit]

                    items_data = [_dbsystem_to_dict(db) for db in items]

                    has_more = params.offset + len(items_data) < len(all_items)
                    next_offset = params.offset + len(items_data) if has_more else None
                    result = {
                        "total": len(all_items),
                        "count": len(items_data),
                        "offset": params.offset,
                        "items": items_data,
                        "has_more": has_more,
                        "next_offset": next_offset,
                    }

                    await ctx.report_progress(0.9, "Formatting output...")

                    if params.response_format == ResponseFormat.JSON:
                        return DatabaseFormatter.to_json(result)
                    return DatabaseFormatter.dbsystem_list_markdown(result)

            except Exception as e:
                error = handle_oci_error(e, "listing DB Systems")
                return format_error_response(error, params.response_format.value)


    @mcp.tool(
        name="oci_database_get_metrics",
        annotations={
            "title": "Get Database Metrics",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def get_database_metrics(params: GetDatabaseMetricsInput, ctx: Context) -> str:
        """Get performance metrics for a database.

        Retrieves CPU, storage, and other performance metrics for an
        Autonomous Database or DB System over a specified time period.

        Args:
            params: GetDatabaseMetricsInput with database_id and time range

        Returns:
            Database performance metrics

        Example:
            {"database_id": "ocid1.autonomousdatabase.oc1...", "hours_back": 24}
        """
        async with observe_tool("oci_database_get_metrics", "database", params.model_dump()):
            await ctx.report_progress(0.1, "Fetching database metrics...")

            try:
                async with get_oci_client() as client:
                    monitoring_client = client.monitoring
                    db_client = client.database

                    # Determine database type and get info
                    await ctx.report_progress(0.2, "Getting database information...")

                    db_info = {}
                    namespace = "oci_autonomous_database"

                    if "autonomousdatabase" in params.database_id:
                        response = await asyncio.to_thread(
                            db_client.get_autonomous_database,
                            autonomous_database_id=params.database_id
                        )
                        db_info = _adb_to_dict(response.data)
                    else:
                        namespace = "oci_database"
                        # DB System metrics
                        response = await asyncio.to_thread(
                            db_client.get_db_system,
                            db_system_id=params.database_id
                        )
                        db_info = _dbsystem_to_dict(response.data)

                    await ctx.report_progress(0.4, "Querying metrics...")

                    # Default metrics for ADB
                    metric_names = params.metric_names or [
                        "CpuUtilization",
                        "StorageUtilization",
                        "Sessions",
                        "ExecuteCount"
                    ]

                    end_time = datetime.now(UTC)
                    start_time = end_time - timedelta(hours=params.hours_back)

                    metrics_data = {}

                    for metric_name in metric_names:
                        try:
                            query = f"{metric_name}[1h].mean()"

                            response = await asyncio.to_thread(
                                monitoring_client.summarize_metrics_data,
                                compartment_id=db_info.get("compartment_id", ""),
                                summarize_metrics_data_details={
                                    "namespace": namespace,
                                    "query": query,
                                    "start_time": start_time.isoformat(),
                                    "end_time": end_time.isoformat(),
                                    "resolution": "1h"
                                }
                            )

                            if response.data:
                                values = [
                                    dp.value
                                    for item in response.data
                                    for dp in (item.aggregated_datapoints or [])
                                    if dp.value is not None
                                ]
                                if values:
                                    metrics_data[metric_name] = {
                                        "current": values[-1] if values else None,
                                        "average": sum(values) / len(values) if values else None,
                                        "max": max(values) if values else None,
                                        "min": min(values) if values else None,
                                    }
                        except Exception:
                            # Skip metrics that fail
                            pass

                    await ctx.report_progress(0.9, "Formatting output...")

                    result = {
                        "database": db_info,
                        "hours_back": params.hours_back,
                        "metrics": metrics_data
                    }

                    if params.response_format == ResponseFormat.JSON:
                        return DatabaseFormatter.to_json(result)
                    return DatabaseFormatter.metrics_markdown(result)

            except Exception as e:
                error = handle_oci_error(e, "getting database metrics")
                return format_error_response(error, params.response_format.value)


    @mcp.tool(
        name="oci_database_list_backups",
        annotations={
            "title": "List Database Backups",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def list_database_backups(params: ListBackupsInput, ctx: Context) -> str:
        """List backups for a database or compartment.

        Retrieves backup history for an Autonomous Database or DB System,
        or all backups in a compartment.

        Args:
            params: ListBackupsInput with database_id or compartment_id

        Returns:
            List of database backups

        Example:
            {"database_id": "ocid1.autonomousdatabase.oc1...", "limit": 20}
        """
        async with observe_tool("oci_database_list_backups", "database", params.model_dump()):
            await ctx.report_progress(0.1, "Fetching database backups...")

            try:
                async with get_oci_client() as client:
                    db_client = client.database

                    items = []

                    is_autonomous = (
                        params.database_type.value == "autonomous"
                        or (params.database_id and "autonomousdatabase" in params.database_id)
                    )
                    if is_autonomous:
                        await ctx.report_progress(0.3, "Listing ADB backups...")

                        if params.database_id:
                            response = await asyncio.to_thread(
                                db_client.list_autonomous_database_backups,
                                autonomous_database_id=params.database_id,
                                limit=params.limit
                            )
                        elif params.compartment_id:
                            response = await asyncio.to_thread(
                                db_client.list_autonomous_database_backups,
                                compartment_id=params.compartment_id,
                                limit=params.limit
                            )
                        else:
                            return "Error: Either database_id or compartment_id is required."

                        items = [_adb_backup_to_dict(b) for b in (response.data or [])]

                    else:
                        await ctx.report_progress(0.3, "Listing DB System backups...")

                        if params.database_id:
                            # For DB System, we need the database OCID, not DB System OCID
                            response = await asyncio.to_thread(
                                db_client.list_backups,
                                database_id=params.database_id,
                                limit=params.limit
                            )
                        elif params.compartment_id:
                            response = await asyncio.to_thread(
                                db_client.list_backups,
                                compartment_id=params.compartment_id,
                                limit=params.limit
                            )
                        else:
                            return "Error: Either database_id or compartment_id is required."

                        items = [_dbsystem_backup_to_dict(b) for b in (response.data or [])]

                    await ctx.report_progress(0.9, "Formatting output...")

                    result = {
                        "items": items,
                        "count": len(items)
                    }

                    if params.response_format == ResponseFormat.JSON:
                        return DatabaseFormatter.to_json(result)
                    return DatabaseFormatter.backup_list_markdown(result)

            except Exception as e:
                error = handle_oci_error(e, "listing database backups")
                return format_error_response(error, params.response_format.value)


# Helper functions for converting OCI objects to dicts
def _adb_to_dict(db: Any, include_connection: bool = False) -> dict:
    """Convert Autonomous Database object to dict."""
    result = {
        "id": db.id,
        "display_name": db.display_name,
        "compartment_id": db.compartment_id,
        "lifecycle_state": db.lifecycle_state,
        "db_name": db.db_name,
        "db_workload": getattr(db, "db_workload", "N/A"),
        "cpu_core_count": getattr(db, "cpu_core_count", 0),
        "data_storage_size_in_tbs": getattr(db, "data_storage_size_in_tbs", 0),
        "is_free_tier": getattr(db, "is_free_tier", False),
        "is_auto_scaling_enabled": getattr(db, "is_auto_scaling_enabled", False),
        "time_created": str(db.time_created) if db.time_created else "",
    }

    if include_connection and hasattr(db, "connection_strings") and db.connection_strings:
        conn = db.connection_strings
        result["connection_strings"] = {
            "high": getattr(conn, "high", None),
            "medium": getattr(conn, "medium", None),
            "low": getattr(conn, "low", None),
        }

    return result


def _dbsystem_to_dict(db: Any) -> dict:
    """Convert DB System object to dict."""
    return {
        "id": db.id,
        "display_name": db.display_name,
        "compartment_id": db.compartment_id,
        "lifecycle_state": db.lifecycle_state,
        "availability_domain": getattr(db, "availability_domain", ""),
        "shape": getattr(db, "shape", ""),
        "cpu_core_count": getattr(db, "cpu_core_count", 0),
        "node_count": getattr(db, "node_count", 1),
        "data_storage_size_in_gbs": getattr(db, "data_storage_size_in_gbs", 0),
        "time_created": str(db.time_created) if db.time_created else "",
    }


def _adb_backup_to_dict(backup: Any) -> dict:
    """Convert ADB backup to dict."""
    return {
        "id": backup.id,
        "database_id": backup.autonomous_database_id,
        "display_name": getattr(backup, "display_name", ""),
        "type": getattr(backup, "type", "FULL"),
        "lifecycle_state": backup.lifecycle_state,
        "database_size_in_gbs": getattr(backup, "database_size_in_tbs", 0) * 1024,
        "time_started": str(backup.time_started) if backup.time_started else "",
        "time_ended": (
            str(backup.time_ended)
            if hasattr(backup, "time_ended") and backup.time_ended else ""
        ),
    }


def _dbsystem_backup_to_dict(backup: Any) -> dict:
    """Convert DB System backup to dict."""
    return {
        "id": backup.id,
        "database_id": backup.database_id,
        "display_name": getattr(backup, "display_name", ""),
        "type": getattr(backup, "type", "FULL"),
        "lifecycle_state": backup.lifecycle_state,
        "database_size_in_gbs": getattr(backup, "database_size_in_gbs", 0),
        "time_started": str(backup.time_started) if backup.time_started else "",
        "time_ended": (
            str(backup.time_ended)
            if hasattr(backup, "time_ended") and backup.time_ended else ""
        ),
    }
