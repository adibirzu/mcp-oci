"""
OCI Compute domain tool implementations.

Uses FastMCP patterns with Pydantic models and proper error handling.
"""
import asyncio
import os
from typing import Any

from fastmcp import Context, FastMCP

from mcp_server_oci.core.client import get_client_manager
from mcp_server_oci.core.errors import format_error_response, handle_oci_error
from mcp_server_oci.core.formatters import ResponseFormat

from .formatters import ComputeFormatter
from .models import (
    GetInstanceInput,
    InstanceActionInput,
    ListInstancesInput,
)


def register_compute_tools(mcp: FastMCP) -> None:
    """Register all compute domain tools with the MCP server."""

    @mcp.tool(
        name="oci_compute_list_instances",
        annotations={
            "title": "List Compute Instances",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def list_instances(params: ListInstancesInput, ctx: Context) -> str:
        """List compute instances in a compartment with filtering and pagination.

        Retrieves instances with their current state, shape, and optionally
        IP addresses. Supports filtering by lifecycle state and display name.

        Args:
            params: ListInstancesInput with compartment_id, lifecycle_state,
                   limit, offset, and response_format

        Returns:
            Instance list in requested format (markdown table or json)

        Example:
            {"compartment_id": "ocid1.compartment...", "lifecycle_state": "RUNNING", "limit": 20}
        """
        try:
            client_mgr = get_client_manager()
            compute_client = client_mgr.compute

            # Get compartment ID from params or environment
            compartment_id = params.compartment_id or os.getenv("COMPARTMENT_OCID")
            if not compartment_id:
                msg = (
                    "Compartment OCID required. "
                    "Provide compartment_id or set COMPARTMENT_OCID env var."
                )
                return format_error_response(msg, params.response_format.value)

            # Build query parameters
            kwargs = {"compartment_id": compartment_id, "limit": params.limit}
            if params.lifecycle_state:
                kwargs["lifecycle_state"] = params.lifecycle_state.value

            # Execute API call
            response = await asyncio.to_thread(
                compute_client.list_instances,
                **kwargs
            )

            # Process instances
            instances = []
            for inst in response.data:
                instance_data = {
                    "id": inst.id,
                    "display_name": inst.display_name,
                    "lifecycle_state": inst.lifecycle_state,
                    "shape": inst.shape,
                    "availability_domain": inst.availability_domain,
                    "fault_domain": inst.fault_domain,
                    "time_created": inst.time_created.isoformat() if inst.time_created else None,
                    "compartment_id": inst.compartment_id,
                    "public_ip": None,
                    "private_ip": None,
                }

                # Filter by display name if provided
                name_filter = params.display_name
                if name_filter and name_filter.lower() not in inst.display_name.lower():
                    continue

                instances.append(instance_data)

            # Fetch IPs if requested (slower)
            if params.include_ips and instances:
                instances = await _fetch_instance_ips(client_mgr, instances)

            # Build output
            has_more = len(response.data) == params.limit
            next_offset = params.offset + len(instances) if has_more else None
            output_data = {
                "total": len(instances),
                "count": len(instances),
                "offset": params.offset,
                "instances": instances,
                "has_more": has_more,
                "next_offset": next_offset,
            }

            if params.response_format == ResponseFormat.JSON:
                return ComputeFormatter.to_json(output_data)
            return ComputeFormatter.instances_markdown(output_data)

        except Exception as e:
            error = handle_oci_error(e, "listing instances")
            return format_error_response(error, params.response_format.value)


    @mcp.tool(
        name="oci_compute_get_instance",
        annotations={
            "title": "Get Instance Details",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def get_instance(params: GetInstanceInput, ctx: Context) -> str:
        """Get detailed information about a specific compute instance.

        Retrieves full instance details including shape configuration,
        network info, and optionally recent metrics.

        Args:
            params: GetInstanceInput with instance_id and include_metrics

        Returns:
            Instance details in requested format
        """
        try:
            client_mgr = get_client_manager()
            compute_client = client_mgr.compute

            response = await asyncio.to_thread(
                compute_client.get_instance,
                params.instance_id
            )

            inst = response.data

            instance_data = {
                "id": inst.id,
                "display_name": inst.display_name,
                "lifecycle_state": inst.lifecycle_state,
                "shape": inst.shape,
                "availability_domain": inst.availability_domain,
                "fault_domain": inst.fault_domain,
                "time_created": inst.time_created.isoformat() if inst.time_created else None,
                "compartment_id": inst.compartment_id,
                "region": inst.region,
                "public_ip": None,
                "private_ip": None,
            }

            # Get IPs
            instance_data = (await _fetch_instance_ips(client_mgr, [instance_data]))[0]

            # Get metrics if requested
            if params.include_metrics:
                instance_data["metrics"] = await _fetch_instance_metrics(
                    client_mgr, inst.id, inst.compartment_id
                )

            if params.response_format == ResponseFormat.JSON:
                return ComputeFormatter.to_json(instance_data)
            return ComputeFormatter.instance_detail_markdown(instance_data)

        except Exception as e:
            error = handle_oci_error(e, "getting instance details")
            return format_error_response(error, params.response_format.value)


    @mcp.tool(
        name="oci_compute_start_instance",
        annotations={
            "title": "Start Compute Instance",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def start_instance(params: InstanceActionInput, ctx: Context) -> str:
        """Start a stopped compute instance.

        Initiates the start action on an instance. Requires ALLOW_MUTATIONS=true.

        Args:
            params: InstanceActionInput with instance_id

        Returns:
            Action result with status
        """
        # Check mutations allowed
        if os.getenv("ALLOW_MUTATIONS", "").lower() != "true":
            return format_error_response(
                "Mutations not allowed. Set ALLOW_MUTATIONS=true to enable.",
                params.response_format.value
            )

        try:
            client_mgr = get_client_manager()
            compute_client = client_mgr.compute

            # Get current state first
            current = await asyncio.to_thread(
                compute_client.get_instance,
                params.instance_id
            )
            previous_state = current.data.lifecycle_state

            # Perform action
            await asyncio.to_thread(
                compute_client.instance_action,
                params.instance_id,
                "START"
            )

            result = {
                "success": True,
                "instance_id": params.instance_id,
                "action": "start",
                "previous_state": previous_state,
                "target_state": "RUNNING",
                "message": "Start action initiated successfully. Instance will be running shortly."
            }

            if params.response_format == ResponseFormat.JSON:
                return ComputeFormatter.to_json(result)
            return ComputeFormatter.action_result_markdown(result)

        except Exception as e:
            error = handle_oci_error(e, "starting instance")
            return format_error_response(error, params.response_format.value)


    @mcp.tool(
        name="oci_compute_stop_instance",
        annotations={
            "title": "Stop Compute Instance",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def stop_instance(params: InstanceActionInput, ctx: Context) -> str:
        """Stop a running compute instance.

        Initiates the stop action on an instance. Requires ALLOW_MUTATIONS=true.
        Use force=true for a hard stop (RESET action).

        Args:
            params: InstanceActionInput with instance_id and force option

        Returns:
            Action result with status
        """
        if os.getenv("ALLOW_MUTATIONS", "").lower() != "true":
            return format_error_response(
                "Mutations not allowed. Set ALLOW_MUTATIONS=true to enable.",
                params.response_format.value
            )

        try:
            client_mgr = get_client_manager()
            compute_client = client_mgr.compute

            # Get current state first
            current = await asyncio.to_thread(
                compute_client.get_instance,
                params.instance_id
            )
            previous_state = current.data.lifecycle_state

            # Perform action
            action = "RESET" if params.force else "STOP"
            await asyncio.to_thread(
                compute_client.instance_action,
                params.instance_id,
                action
            )

            stop_type = "Hard" if params.force else "Soft"
            result = {
                "success": True,
                "instance_id": params.instance_id,
                "action": "stop" + (" (forced)" if params.force else ""),
                "previous_state": previous_state,
                "target_state": "STOPPED",
                "message": f"{stop_type} stop initiated. Instance will be stopped shortly.",
            }

            if params.response_format == ResponseFormat.JSON:
                return ComputeFormatter.to_json(result)
            return ComputeFormatter.action_result_markdown(result)

        except Exception as e:
            error = handle_oci_error(e, "stopping instance")
            return format_error_response(error, params.response_format.value)


    @mcp.tool(
        name="oci_compute_restart_instance",
        annotations={
            "title": "Restart Compute Instance",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def restart_instance(params: InstanceActionInput, ctx: Context) -> str:
        """Restart a compute instance (soft reset).

        Performs a soft reset on the instance. Requires ALLOW_MUTATIONS=true.
        Use force=true for a hard reset.

        Args:
            params: InstanceActionInput with instance_id and force option

        Returns:
            Action result with status
        """
        if os.getenv("ALLOW_MUTATIONS", "").lower() != "true":
            return format_error_response(
                "Mutations not allowed. Set ALLOW_MUTATIONS=true to enable.",
                params.response_format.value
            )

        try:
            client_mgr = get_client_manager()
            compute_client = client_mgr.compute

            # Get current state first
            current = await asyncio.to_thread(
                compute_client.get_instance,
                params.instance_id
            )
            previous_state = current.data.lifecycle_state

            # Perform action
            action = "RESET" if params.force else "SOFTRESET"
            await asyncio.to_thread(
                compute_client.instance_action,
                params.instance_id,
                action
            )

            restart_type = "Hard" if params.force else "Soft"
            result = {
                "success": True,
                "instance_id": params.instance_id,
                "action": "restart" + (" (hard)" if params.force else " (soft)"),
                "previous_state": previous_state,
                "target_state": "RUNNING",
                "message": f"{restart_type} restart initiated. Instance will be running shortly.",
            }

            if params.response_format == ResponseFormat.JSON:
                return ComputeFormatter.to_json(result)
            return ComputeFormatter.action_result_markdown(result)

        except Exception as e:
            error = handle_oci_error(e, "restarting instance")
            return format_error_response(error, params.response_format.value)


# =============================================================================
# Helper Functions
# =============================================================================

async def _fetch_instance_ips(
    client_mgr: Any,
    instances: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Fetch IP addresses for instances."""
    import oci

    try:
        network_client = client_mgr.get_client(oci.core.VirtualNetworkClient)
        compute_client = client_mgr.compute

        for inst in instances:
            try:
                # Get VNICs attached to instance
                vnic_attachments = await asyncio.to_thread(
                    compute_client.list_vnic_attachments,
                    compartment_id=inst["compartment_id"],
                    instance_id=inst["id"]
                )

                for attachment in vnic_attachments.data:
                    if attachment.lifecycle_state == "ATTACHED" and attachment.vnic_id:
                        vnic = await asyncio.to_thread(
                            network_client.get_vnic,
                            attachment.vnic_id
                        )
                        if vnic.data.is_primary:
                            inst["private_ip"] = vnic.data.private_ip
                            inst["public_ip"] = vnic.data.public_ip
                            break
            except Exception:
                # Skip IP fetching errors for individual instances
                pass

    except Exception:
        # Return instances without IPs if network queries fail
        pass

    return instances


async def _fetch_instance_metrics(
    client_mgr: Any,
    instance_id: str,
    compartment_id: str
) -> dict[str, Any]:
    """Fetch recent metrics for an instance."""
    from datetime import datetime, timedelta

    import oci

    metrics = {}

    try:
        monitoring_client = client_mgr.get_client(oci.monitoring.MonitoringClient)

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)

        metric_names = ["CpuUtilization", "MemoryUtilization"]

        for metric_name in metric_names:
            try:
                query = f'{metric_name}[1h]{{resourceId="{instance_id}"}}.mean()'

                response = await asyncio.to_thread(
                    monitoring_client.summarize_metrics_data,
                    compartment_id,
                    oci.monitoring.models.SummarizeMetricsDataDetails(
                        namespace="oci_computeagent",
                        query=query,
                        start_time=start_time,
                        end_time=end_time
                    )
                )

                if response.data:
                    values = [dp.value for dp in response.data[0].aggregated_datapoints]
                    if values:
                        metrics[metric_name] = {
                            "statistics": {
                                "average": sum(values) / len(values),
                                "max": max(values),
                                "min": min(values),
                            }
                        }
            except Exception:
                # Skip individual metric errors
                pass

    except Exception:
        # Return empty metrics if monitoring fails
        pass

    return metrics
