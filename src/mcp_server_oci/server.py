"""
OCI MCP Server - Main Entry Point

FastMCP server implementation with:
- Lifespan management for OCI client and observability
- Progressive disclosure through tool discovery
- Domain-organized tool registration
- Health and diagnostic endpoints

Environment Variables:
- OCI_MCP_NAME: Server name (default: oci-mcp)
- OCI_MCP_TRANSPORT: Transport mode (stdio, streamable_http)
- OCI_MCP_PORT: HTTP port if using streamable_http
- OCI_MCP_LOG_LEVEL: Logging level
- See core/client.py for OCI configuration variables
"""
import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastmcp import Context, FastMCP

from mcp_server_oci.config import get_config
from mcp_server_oci.core import (
    HealthStatus,
    ServerManifest,
    check_observability_health,
    clear_all_caches,
    get_all_cache_stats,
    # Cache
    get_cache,
    get_client_manager,
    get_logger,
    # Shared memory
    get_shared_store,
    init_observability,
)

# Import compute models early for alias tool type hints
from mcp_server_oci.tools.compute.formatters import ComputeFormatter
from mcp_server_oci.tools.compute.models import (
    GetInstanceMetricsInput,
    InstanceActionInput,
    ListInstancesInput,
)
from mcp_server_oci.tools.compute.tools import (
    _fetch_instance_ips,
    _fetch_instance_metrics,
)

# Get configuration
config = get_config()
logger = get_logger("oci-mcp.server")


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncGenerator[None, None]:
    """
    Initialize resources on startup, cleanup on shutdown.

    This context manager:
    1. Initializes observability (logging, tracing)
    2. Initializes the OCI client manager
    3. Yields context with initialized resources
    4. Cleans up on shutdown
    """
    logger.info("Starting OCI MCP Server", version=config.server.version)

    # Initialize observability (OCI APM + Logging)
    init_observability(
        service_name=config.server.name,
        service_version=config.server.version
    )

    # Initialize OCI client
    client_manager = get_client_manager()
    try:
        await client_manager.initialize()
        logger.info(
            "OCI client initialized",
            auth_method=client_manager.auth_method,
            region=client_manager.region
        )
    except Exception as e:
        logger.warning(f"OCI client initialization failed: {e}")
        # Server can still start - some tools may work without OCI connection

    # Initialize caches (lazy initialization - just ensure they're created)
    _ = get_cache("static")
    _ = get_cache("config")
    _ = get_cache("operational")
    _ = get_cache("metrics")
    logger.info("Cache tiers initialized")

    # Initialize shared store (in-memory fallback if ATP not configured)
    shared_store = get_shared_store()
    logger.info(f"Shared store initialized: {type(shared_store).__name__}")

    # Yield context for tool access
    yield {
        "oci_client": client_manager,
        "config": config,
        "shared_store": shared_store,
    }

    # Cleanup on shutdown
    logger.info("Shutting down OCI MCP Server")
    await clear_all_caches()
    client_manager.clear_cache()


# Initialize FastMCP Server with lifespan
mcp = FastMCP(
    name=config.server.name,
    instructions="""Oracle Cloud Infrastructure MCP Server providing comprehensive
cloud management capabilities through the Model Context Protocol.

Use `oci_search_tools` to discover available tools.
Use `oci_list_domains` to see capability areas.
Use `oci_ping` to verify server health.
""",
    lifespan=app_lifespan,
)


# =============================================================================
# Health & Discovery Tools (Tier 1 - Instant)
# =============================================================================

@mcp.tool(
    name="oci_ping",
    annotations={
        "title": "OCI Server Health Check",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def oci_ping() -> str:
    """
    Simple health check to verify the MCP server is responsive.

    Returns server status, version, and OCI connection health.
    Should respond in <500ms.

    Returns:
        Health status with server info and OCI connection state
    """
    client = get_client_manager()
    oci_health = await client.health_check()
    obs_health = await check_observability_health()

    status = HealthStatus(
        healthy=oci_health.get("healthy", False),
        server_name=config.server.name,
        version=config.server.version,
        oci_connected=oci_health.get("healthy", False),
        auth_method=oci_health.get("auth_method"),
        region=oci_health.get("region"),
        observability_enabled=obs_health.get("logging_enabled", False),
        details={
            "oci": oci_health,
            "observability": obs_health,
        }
    )

    return status.model_dump_json(indent=2)


@mcp.tool(
    name="oci_list_domains",
    annotations={
        "title": "List OCI Tool Domains",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def oci_list_domains(include_tool_count: bool = True) -> str:
    """
    List available OCI tool domains.

    Returns all available domains with descriptions and tool counts.
    Use this to understand what capability areas are available.

    Args:
        include_tool_count: Include number of tools per domain

    Returns:
        List of domains with descriptions
    """
    # Domain definitions
    domains = {
        "compute": {
            "description": "Instance management, shapes, and performance metrics",
            "tools": [
                "list_instances", "start_instance", "stop_instance",
                "restart_instance", "get_instance_metrics"
            ],
        },
        "cost": {
            "description": "Cost analysis, budgeting, forecasting, and FinOps",
            "tools": [
                "oci_cost_get_summary", "oci_cost_by_service",
                "oci_cost_by_compartment", "oci_cost_monthly_trend",
                "oci_cost_detect_anomalies"
            ],
        },
        "database": {
            "description": "Autonomous Database, DB Systems, and MySQL management",
            "tools": [
                "oci_database_list_autonomous", "oci_database_get_autonomous",
                "oci_database_start_autonomous", "oci_database_stop_autonomous",
                "oci_database_list_dbsystems"
            ],
        },
        "network": {
            "description": "VCN, Subnet, Security List management and analysis",
            "tools": [
                "oci_network_list_vcns", "oci_network_get_vcn",
                "oci_network_list_subnets", "oci_network_list_security_lists",
                "oci_network_analyze_security"
            ],
        },
        "security": {
            "description": "IAM, Cloud Guard, and security policy management",
            "tools": [
                "oci_security_list_users", "oci_security_get_user",
                "oci_security_list_groups", "oci_security_list_policies",
                "oci_security_list_cloud_guard_problems", "oci_security_audit"
            ],
        },
        "observability": {
            "description": "Logging Analytics, monitoring, alarms, and metrics",
            "tools": [
                "oci_observability_get_metrics", "oci_observability_list_alarms",
                "oci_observability_get_alarm", "oci_observability_query_logs",
                "oci_observability_get_log_source"
            ],
        },
        "skills": {
            "description": "High-level workflow skills combining operations",
            "tools": ["oci_skill_troubleshoot_instance"],
        },
        "discovery": {
            "description": "Tool discovery and server information",
            "tools": [
                "oci_ping", "oci_list_domains",
                "oci_search_tools", "oci_get_manifest"
            ],
        },
    }

    # Format output
    lines = ["# Available OCI Domains\n"]
    for name, info in sorted(domains.items()):
        tool_count = len(info["tools"])
        if include_tool_count:
            lines.append(f"## {name} ({tool_count} tools)")
        else:
            lines.append(f"## {name}")
        lines.append(f"{info['description']}\n")

    return "\n".join(lines)


@mcp.tool(
    name="oci_search_tools",
    annotations={
        "title": "Search OCI Tools",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def oci_search_tools(
    query: str,
    domain: str | None = None,
    detail_level: str = "summary"
) -> str:
    """
    Search for OCI tools matching a query.

    Use this to discover available tools before executing them.
    Supports different detail levels for efficient context usage.

    Args:
        query: Search keywords (e.g., "cost", "instances", "logs")
        domain: Optional filter by domain (compute, observability, etc.)
        detail_level: Level of detail: 'name_only', 'summary', or 'full'

    Returns:
        Matching tools at requested detail level

    Example:
        {"query": "instance", "detail_level": "summary"}
        {"query": "metrics", "domain": "observability"}
    """
    all_tools = await mcp.get_tools()

    results = []
    q = query.lower()
    d = domain.lower() if domain else None

    for tool in all_tools:
        name = tool.name
        desc = tool.description or ""

        # Domain filtering
        if d and d not in name.lower() and d not in desc.lower():
            continue

        # Query matching
        if q in name.lower() or q in desc.lower():
            results.append({
                "name": name,
                "description": desc,
                "schema": tool.inputSchema if detail_level == "full" else None,
            })

    if not results:
        return f"No tools found matching '{query}'. Try a broader query or different domain."

    # Format based on detail level
    if detail_level == "name_only":
        return "\n".join(t["name"] for t in results)
    elif detail_level == "summary":
        lines = ["## Matching Tools\n"]
        for t in results:
            lines.append(f"**{t['name']}**")
            desc = t['description']
            desc_line = f"  {desc[:100]}...\n" if len(desc) > 100 else f"  {desc}\n"
            lines.append(desc_line)
        return "\n".join(lines)
    else:  # full
        return json.dumps(results, indent=2)


@mcp.tool(
    name="oci_get_cache_stats",
    annotations={
        "title": "Get Cache Statistics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_cache_stats() -> str:
    """
    Get cache performance statistics for all cache tiers.

    Returns hit rates, eviction counts, and cache sizes for
    static, config, operational, and metrics caches.

    Useful for monitoring and debugging cache effectiveness.
    """
    stats = await get_all_cache_stats()

    lines = ["# Cache Statistics\n"]
    for tier, tier_stats in stats.items():
        lines.append(f"## {tier.title()} Cache")
        lines.append(f"- Hit Rate: {tier_stats['hit_rate']}")
        lines.append(f"- Hits: {tier_stats['hits']}")
        lines.append(f"- Misses: {tier_stats['misses']}")
        lines.append(f"- Evictions: {tier_stats['evictions']}")
        lines.append(f"- Expirations: {tier_stats['expirations']}")
        lines.append(f"- Size: {tier_stats['size']}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("server://manifest")
async def get_manifest() -> str:
    """
    Return server manifest for client optimization.

    Provides server metadata, capabilities, and tool categorization
    for efficient client-side caching and tool discovery.
    """
    manifest = ServerManifest(
        name=config.server.name,
        version=config.server.version,
        description="Unified OCI MCP server with progressive disclosure and skill framework",
        capabilities={
            "skills": {
                "description": "High-level composite workflows that orchestrate multiple tools",
                "available": ["oci_skill_troubleshoot_instance"],
                "domains": ["compute", "observability"],
            },
            "tools": {
                "tier1_instant": [
                    "oci_ping", "oci_search_tools",
                    "oci_list_domains", "oci_get_cache_stats"
                ],
                "tier2_api": [
                    "oci_compute_list_instances",
                    "oci_observability_get_instance_metrics",
                    "oci_observability_execute_log_query",
                    "oci_network_list_vcns", "oci_network_list_subnets",
                    "oci_security_list_users", "oci_security_list_policies"
                ],
                "tier3_heavy": [
                    "oci_security_audit", "oci_skill_troubleshoot_instance"
                ],
                "tier4_admin": [
                    "oci_compute_start_instance",
                    "oci_compute_stop_instance",
                    "oci_compute_restart_instance"
                ],
            }
        },
        domains=[
            {"name": "compute", "tool_count": 5, "skill_count": 1},
            {"name": "cost", "tool_count": 5, "skill_count": 0},
            {"name": "database", "tool_count": 5, "skill_count": 0},
            {"name": "network", "tool_count": 5, "skill_count": 0},
            {"name": "security", "tool_count": 6, "skill_count": 0},
            {"name": "observability", "tool_count": 6, "skill_count": 0},
            {"name": "discovery", "tool_count": 4, "skill_count": 0},
        ],
        environment_variables=[
            "OCI_CONFIG_FILE",
            "OCI_PROFILE",
            "OCI_REGION",
            "COMPARTMENT_OCID",
            "ALLOW_MUTATIONS",
        ],
        usage_guide=(
            "Use oci_list_domains() to discover capabilities, then "
            "oci_search_tools() to find specific tools. Skills are composite "
            "operations that combine multiple tools for complex workflows."
        ),
    )

    return manifest.model_dump_json(indent=2)


# =============================================================================
# Tool Registration
# =============================================================================

# Import domain registration functions
# Import skills registration
from mcp_server_oci.skills import register_skill_tools
from mcp_server_oci.tools.compute import register_compute_tools
from mcp_server_oci.tools.cost import register_cost_tools
from mcp_server_oci.tools.database import register_database_tools
from mcp_server_oci.tools.network import register_network_tools
from mcp_server_oci.tools.observability import register_observability_tools
from mcp_server_oci.tools.security import register_security_tools

# Register all domain tools
register_cost_tools(mcp)
register_compute_tools(mcp)
register_database_tools(mcp)
register_network_tools(mcp)
register_security_tools(mcp)
register_observability_tools(mcp)

# Register skill tools
register_skill_tools(mcp)


# =============================================================================
# Tool Aliases (Backward Compatibility)
# =============================================================================
# These aliases allow agents using shorter tool names to continue working.
# The canonical names follow the pattern: oci_{domain}_{action}_{resource}
# Note: Compute model imports are at the top of the file for type hint resolution.


@mcp.tool(
    name="list_instances",
    annotations={
        "title": "List Compute Instances (Alias)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def list_instances_alias(params: ListInstancesInput, ctx: Context) -> str:
    """
    Alias for oci_compute_list_instances.

    List compute instances in a compartment with filtering and pagination.
    See oci_compute_list_instances for full documentation.
    """
    # Get the registered tool and call it
    tools = await mcp.get_tools()
    for tool in tools:
        if tool.name == "oci_compute_list_instances":
            # Re-use the registered implementation
            break

    # Direct implementation to avoid circular lookup
    import asyncio
    import os

    from mcp_server_oci.core.client import get_client_manager
    from mcp_server_oci.core.errors import format_error_response, handle_oci_error
    from mcp_server_oci.core.formatters import ResponseFormat

    try:
        client_mgr = get_client_manager()
        compute_client = client_mgr.compute

        compartment_id = params.compartment_id or os.getenv("COMPARTMENT_OCID")
        if not compartment_id:
            msg = (
                "Compartment OCID required. "
                "Provide compartment_id or set COMPARTMENT_OCID env var."
            )
            return format_error_response(msg, params.response_format.value)

        kwargs = {"compartment_id": compartment_id, "limit": params.limit}
        if params.lifecycle_state:
            kwargs["lifecycle_state"] = params.lifecycle_state.value

        response = await asyncio.to_thread(
            compute_client.list_instances,
            **kwargs
        )

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

        if params.include_ips and instances:
            instances = await _fetch_instance_ips(client_mgr, instances)

        has_more = len(response.data) == params.limit
        next_offset = params.offset + len(instances) if has_more else None
        output_data = {
            "total": len(instances),
            "count": len(instances),
            "offset": params.offset,
            "instances": instances,
            "has_more": has_more,
            "next_offset": next_offset
        }

        if params.response_format == ResponseFormat.JSON:
            return ComputeFormatter.to_json(output_data)
        return ComputeFormatter.instances_markdown(output_data)

    except Exception as e:
        error = handle_oci_error(e, "listing instances")
        return format_error_response(error, params.response_format.value)


@mcp.tool(
    name="start_instance",
    annotations={
        "title": "Start Compute Instance (Alias)",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def start_instance_alias(params: InstanceActionInput, ctx: Context) -> str:
    """
    Alias for oci_compute_start_instance.

    Start a stopped compute instance. Requires ALLOW_MUTATIONS=true.
    """
    import asyncio
    import os

    from mcp_server_oci.core.client import get_client_manager
    from mcp_server_oci.core.errors import format_error_response, handle_oci_error
    from mcp_server_oci.core.formatters import ResponseFormat

    if os.getenv("ALLOW_MUTATIONS", "").lower() != "true":
        return format_error_response(
            "Mutations not allowed. Set ALLOW_MUTATIONS=true to enable.",
            params.response_format.value
        )

    try:
        client_mgr = get_client_manager()
        compute_client = client_mgr.compute

        current = await asyncio.to_thread(
            compute_client.get_instance,
            params.instance_id
        )
        previous_state = current.data.lifecycle_state

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
    name="stop_instance",
    annotations={
        "title": "Stop Compute Instance (Alias)",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def stop_instance_alias(params: InstanceActionInput, ctx: Context) -> str:
    """
    Alias for oci_compute_stop_instance.

    Stop a running compute instance. Requires ALLOW_MUTATIONS=true.
    """
    import asyncio
    import os

    from mcp_server_oci.core.client import get_client_manager
    from mcp_server_oci.core.errors import format_error_response, handle_oci_error
    from mcp_server_oci.core.formatters import ResponseFormat

    if os.getenv("ALLOW_MUTATIONS", "").lower() != "true":
        return format_error_response(
            "Mutations not allowed. Set ALLOW_MUTATIONS=true to enable.",
            params.response_format.value
        )

    try:
        client_mgr = get_client_manager()
        compute_client = client_mgr.compute

        current = await asyncio.to_thread(
            compute_client.get_instance,
            params.instance_id
        )
        previous_state = current.data.lifecycle_state

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
            "message": f"{stop_type} stop initiated. Instance will be stopped shortly."
        }

        if params.response_format == ResponseFormat.JSON:
            return ComputeFormatter.to_json(result)
        return ComputeFormatter.action_result_markdown(result)

    except Exception as e:
        error = handle_oci_error(e, "stopping instance")
        return format_error_response(error, params.response_format.value)


@mcp.tool(
    name="restart_instance",
    annotations={
        "title": "Restart Compute Instance (Alias)",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def restart_instance_alias(params: InstanceActionInput, ctx: Context) -> str:
    """
    Alias for oci_compute_restart_instance.

    Restart a compute instance. Requires ALLOW_MUTATIONS=true.
    """
    import asyncio
    import os

    from mcp_server_oci.core.client import get_client_manager
    from mcp_server_oci.core.errors import format_error_response, handle_oci_error
    from mcp_server_oci.core.formatters import ResponseFormat

    if os.getenv("ALLOW_MUTATIONS", "").lower() != "true":
        return format_error_response(
            "Mutations not allowed. Set ALLOW_MUTATIONS=true to enable.",
            params.response_format.value
        )

    try:
        client_mgr = get_client_manager()
        compute_client = client_mgr.compute

        current = await asyncio.to_thread(
            compute_client.get_instance,
            params.instance_id
        )
        previous_state = current.data.lifecycle_state

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
            "message": f"{restart_type} restart initiated. Instance will be running."
        }

        if params.response_format == ResponseFormat.JSON:
            return ComputeFormatter.to_json(result)
        return ComputeFormatter.action_result_markdown(result)

    except Exception as e:
        error = handle_oci_error(e, "restarting instance")
        return format_error_response(error, params.response_format.value)


@mcp.tool(
    name="get_instance_metrics",
    annotations={
        "title": "Get Instance Metrics (Alias)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def get_instance_metrics_alias(params: GetInstanceMetricsInput, ctx: Context) -> str:
    """
    Alias for oci_observability_get_instance_metrics.

    Get CPU/Memory metrics for a compute instance.
    """
    import os

    from mcp_server_oci.core.client import get_client_manager
    from mcp_server_oci.core.errors import format_error_response, handle_oci_error
    from mcp_server_oci.core.formatters import ResponseFormat

    try:
        client_mgr = get_client_manager()

        compartment_id = params.compartment_id or os.getenv("COMPARTMENT_OCID")
        if not compartment_id:
            return format_error_response(
                "Compartment OCID required.",
                params.response_format.value
            )

        metrics = await _fetch_instance_metrics(
            client_mgr,
            params.instance_id,
            compartment_id
        )

        result = {
            "instance_id": params.instance_id,
            "metrics": metrics,
            "time_window": params.time_window,
        }

        if params.response_format == ResponseFormat.JSON:
            return ComputeFormatter.to_json(result)

        # Simple markdown output
        lines = [f"# Instance Metrics: {params.instance_id}\n"]
        for name, data in metrics.items():
            lines.append(f"## {name}")
            if "statistics" in data:
                stats = data["statistics"]
                lines.append(f"- Average: {stats.get('average', 'N/A'):.2f}%")
                lines.append(f"- Max: {stats.get('max', 'N/A'):.2f}%")
                lines.append(f"- Min: {stats.get('min', 'N/A'):.2f}%")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        error = handle_oci_error(e, "fetching instance metrics")
        return format_error_response(error, params.response_format.value)


# =============================================================================
# Main Entrypoint
# =============================================================================

def main() -> None:
    """Entry point supporting multiple transports."""
    if config.server.transport == "streamable_http":
        logger.info(f"Starting HTTP server on port {config.server.port}")
        mcp.run(transport="streamable-http", port=config.server.port)
    else:
        logger.info("Starting stdio server")
        mcp.run()


if __name__ == "__main__":
    main()
