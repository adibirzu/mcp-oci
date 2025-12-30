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
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastmcp import FastMCP, Context

from mcp_server_oci.config import get_config
from mcp_server_oci.core import (
    get_client_manager,
    get_logger,
    init_observability,
    check_observability_health,
    ResponseFormat,
    format_response,
    HealthStatus,
    ServerManifest,
)

# Get configuration
config = get_config()
logger = get_logger("oci-mcp.server")


@asynccontextmanager
async def app_lifespan(server: FastMCP):
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
    
    # Yield context for tool access
    yield {
        "oci_client": client_manager,
        "config": config,
    }
    
    # Cleanup on shutdown
    logger.info("Shutting down OCI MCP Server")
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
    obs_health = check_observability_health()
    
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
            "tools": ["list_instances", "start_instance", "stop_instance", "restart_instance", "get_instance_metrics"],
        },
        "cost": {
            "description": "Cost analysis, budgeting, forecasting, and FinOps optimization",
            "tools": ["oci_cost_get_summary", "oci_cost_by_service", "oci_cost_by_compartment", "oci_cost_monthly_trend", "oci_cost_detect_anomalies"],
        },
        "database": {
            "description": "Autonomous Database, DB Systems, and MySQL management",
            "tools": ["oci_database_list_autonomous", "oci_database_get_autonomous", "oci_database_start_autonomous", "oci_database_stop_autonomous", "oci_database_list_dbsystems"],
        },
        "network": {
            "description": "VCN, Subnet, and Security List management with security analysis",
            "tools": ["oci_network_list_vcns", "oci_network_get_vcn", "oci_network_list_subnets", "oci_network_list_security_lists", "oci_network_analyze_security"],
        },
        "security": {
            "description": "IAM, Cloud Guard, and security policy management",
            "tools": ["oci_security_list_users", "oci_security_get_user", "oci_security_list_groups", "oci_security_list_policies", "oci_security_list_cloud_guard_problems", "oci_security_audit"],
        },
        "observability": {
            "description": "Logging Analytics, monitoring, alarms, and metrics queries",
            "tools": ["oci_observability_get_metrics", "oci_observability_list_alarms", "oci_observability_get_alarm", "oci_observability_query_logs", "oci_observability_get_log_source"],
        },
        "skills": {
            "description": "High-level workflow skills that combine multiple operations",
            "tools": ["troubleshoot_instance"],
        },
        "discovery": {
            "description": "Tool discovery and server information",
            "tools": ["oci_ping", "oci_list_domains", "oci_search_tools", "oci_get_manifest"],
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
    domain: Optional[str] = None,
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
        if d:
            # Check if domain string is in name or description
            if d not in name.lower() and d not in desc.lower():
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
            lines.append(f"  {t['description'][:100]}...\n" if len(t['description']) > 100 else f"  {t['description']}\n")
        return "\n".join(lines)
    else:  # full
        return json.dumps(results, indent=2)


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
        description="Unified OCI MCP server with progressive disclosure",
        capabilities={
            "skills": ["compute_management", "observability", "network_management", "security_management", "troubleshooting"],
            "tools": {
                "tier1_instant": ["oci_ping", "oci_search_tools", "oci_list_domains"],
                "tier2_api": ["list_instances", "get_instance_metrics", "get_logs", "oci_network_list_vcns", "oci_network_list_subnets", "oci_security_list_users", "oci_security_list_policies"],
                "tier3_heavy": ["oci_security_audit"],
                "tier4_admin": ["start_instance", "stop_instance", "restart_instance"],
            }
        },
        domains=[
            {"name": "compute", "tool_count": 5},
            {"name": "cost", "tool_count": 5},
            {"name": "database", "tool_count": 5},
            {"name": "network", "tool_count": 5},
            {"name": "security", "tool_count": 6},
            {"name": "observability", "tool_count": 5},
            {"name": "skills", "tool_count": 1},
            {"name": "discovery", "tool_count": 4},
        ],
        environment_variables=[
            "OCI_CONFIG_FILE",
            "OCI_PROFILE",
            "OCI_REGION",
            "COMPARTMENT_OCID",
            "ALLOW_MUTATIONS",
        ],
        usage_guide="Use oci_list_domains() to discover capabilities, then oci_search_tools() to find specific tools.",
    )
    
    return manifest.model_dump_json(indent=2)


# =============================================================================
# Tool Registration
# =============================================================================

# Import domain registration functions
from mcp_server_oci.tools.cost import register_cost_tools
from mcp_server_oci.tools.compute import register_compute_tools
from mcp_server_oci.tools.database import register_database_tools
from mcp_server_oci.tools.network import register_network_tools
from mcp_server_oci.tools.security import register_security_tools
from mcp_server_oci.tools.observability import register_observability_tools

# Import skills
from mcp_server_oci.skills.troubleshoot import troubleshoot_instance

# Register all domain tools
register_cost_tools(mcp)
register_compute_tools(mcp)
register_database_tools(mcp)
register_network_tools(mcp)
register_security_tools(mcp)
register_observability_tools(mcp)

# Register skill tools
mcp.tool(troubleshoot_instance)


# =============================================================================
# Main Entrypoint
# =============================================================================

def main():
    """Entry point supporting multiple transports."""
    if config.server.transport == "streamable_http":
        logger.info(f"Starting HTTP server on port {config.server.port}")
        mcp.run(transport="streamable_http", port=config.server.port)
    else:
        logger.info("Starting stdio server")
        mcp.run()


if __name__ == "__main__":
    main()
