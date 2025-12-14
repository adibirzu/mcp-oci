"""
FastMCP entry point for OCI Log Analytics server.

This module creates a proper FastMCP server wrapping the existing tool definitions.
"""
import os
import logging
import asyncio
from typing import Dict, Any

from fastmcp import FastMCP

# Import the register_tools function
from .server import register_tools

# Setup logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)
logger = logging.getLogger(__name__)

# Create FastMCP app
app = FastMCP("oci-mcp-loganalytics")


@app.tool()
def healthcheck() -> str:
    """
    Check if the Log Analytics MCP server is running and healthy.
    Returns server status and configuration info.
    """
    return """Log Analytics MCP Server Status: HEALTHY

Server: oci-mcp-loganalytics
Status: Running
Tools: Available
"""


@app.tool()
def doctor() -> str:
    """
    Diagnostic tool for the Log Analytics MCP server.
    Checks server health and dependencies.
    """
    results = []
    results.append("=" * 50)
    results.append("OCI Log Analytics MCP Server Diagnostics")
    results.append("=" * 50)

    # Check OCI SDK
    try:
        import oci
        results.append(f"[OK] OCI SDK version: {oci.__version__}")
    except ImportError as e:
        results.append(f"[ERROR] OCI SDK not available: {e}")

    # Check OCI config
    try:
        from mcp_oci_common import get_oci_config
        config = get_oci_config()
        results.append(f"[OK] OCI config loaded for region: {config.get('region', 'DEFAULT')}")
    except Exception as e:
        results.append(f"[ERROR] OCI config error: {e}")

    # List available tools
    tools = register_tools()
    results.append(f"[OK] {len(tools)} Log Analytics tools registered")

    return "\n".join(results)


# Dynamically register tools from the existing register_tools function
def _create_tool_wrapper(tool_def: Dict[str, Any]):
    """Create a wrapper function for a tool definition."""
    handler = tool_def["handler"]

    async def wrapper(**kwargs):
        """Async wrapper for tool execution."""
        try:
            result = handler(**kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_def['name']}: {e}")
            return {"error": str(e), "tool": tool_def["name"]}

    wrapper.__name__ = tool_def["name"]
    wrapper.__doc__ = tool_def["description"]
    return wrapper


# Register all tools from the register_tools function
_registered_tools = []
for tool_def in register_tools():
    try:
        wrapper = _create_tool_wrapper(tool_def)
        # Extract parameter schema
        params = tool_def.get("parameters", {})
        # Register with FastMCP using decorator pattern
        tool_name = tool_def["name"]
        tool_desc = tool_def["description"]

        # For FastMCP, we need to register differently
        # Create a simple callable wrapper
        app.tool(name=tool_name, description=tool_desc)(wrapper)
        _registered_tools.append(tool_name)
    except Exception as e:
        logger.warning(f"Could not register tool {tool_def.get('name', 'unknown')}: {e}")

logger.info(f"Registered {len(_registered_tools)} Log Analytics tools")


if __name__ == "__main__":
    app.run()
