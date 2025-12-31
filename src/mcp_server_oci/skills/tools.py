"""
Skill tool registrations for MCP server.

This module handles the registration of skill tools with FastMCP,
following the same pattern as domain tools (compute, cost, etc.).
"""
from __future__ import annotations

from mcp.server.fastmcp import Context, FastMCP

from .troubleshoot import TroubleshootInstanceInput, troubleshoot_instance


def register_skill_tools(mcp: FastMCP) -> None:
    """Register all skill tools with the MCP server."""

    @mcp.tool(
        name="oci_skill_troubleshoot_instance",
        annotations={
            "title": "Troubleshoot Compute Instance",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def skill_troubleshoot_instance(
        params: TroubleshootInstanceInput, ctx: Context
    ) -> str:
        """
        Perform comprehensive health check on a compute instance.

        This skill orchestrates multiple tools to provide:
        - Instance state verification
        - CPU/memory metric analysis with trend detection
        - Log error pattern detection (requires Log Analytics)
        - Active alarm identification
        - Actionable recommendations

        Args:
            params: TroubleshootInstanceInput with instance_id and options

        Returns:
            Troubleshooting report in requested format (markdown or json)

        Example:
            {"instance_id": "ocid1.instance.oc1.xxx", "time_window": "1h"}
        """
        return await troubleshoot_instance(params, ctx)
