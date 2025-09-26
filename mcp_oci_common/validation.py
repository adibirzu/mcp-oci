"""
MCP Tool Validation Utilities

Provides validation functions for MCP tool names and other MCP compliance checks.
"""

import re
import logging
from typing import List, Dict, Any

# MCP tool name regex: only letters, digits, underscores, and hyphens, 1-64 characters
MCP_TOOL_NAME_REGEX = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

logger = logging.getLogger(__name__)


def validate_tool_name(name: str) -> bool:
    """
    Validate a tool name against MCP specifications.

    Args:
        name: The tool name to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(name, str):
        return False
    return bool(MCP_TOOL_NAME_REGEX.match(name))


def validate_tools(tools: List[Any], server_name: str = "unknown") -> List[str]:
    """
    Validate a list of MCP tools for compliance.

    Args:
        tools: List of tool objects (dictionaries or FastMCP Tool objects)
        server_name: Name of the server for logging

    Returns:
        List of error messages for invalid tools
    """
    errors = []

    for tool in tools:
        # Handle FastMCP Tool objects
        if hasattr(tool, 'name'):
            name = getattr(tool, 'name', '')
        # Handle dictionary-based tools
        elif isinstance(tool, dict):
            name = tool.get('name', '')
        else:
            errors.append(f"Tool is not a valid tool object in {server_name}")
            continue

        if not name:
            errors.append(f"Tool missing name in {server_name}")
            continue

        if not validate_tool_name(name):
            errors.append(f"Tool name '{name}' in {server_name} violates MCP regex ^[a-zA-Z0-9_-]{{1,64}}$")

    return errors


def validate_and_log_tools(tools: List[Any], server_name: str = "unknown") -> bool:
    """
    Validate tools and log any errors. Exits with error code if validation fails.

    Args:
        tools: List of tool dictionaries with 'name' key
        server_name: Name of the server for logging

    Returns:
        True if all tools are valid, False otherwise
    """
    errors = validate_tools(tools, server_name)

    if errors:
        logger.error(f"MCP Tool Validation Failed for {server_name}:")
        for error in errors:
            logger.error(f"  - {error}")
        return False

    logger.info(f"MCP Tool Validation Passed for {server_name} ({len(tools)} tools)")
    return True
