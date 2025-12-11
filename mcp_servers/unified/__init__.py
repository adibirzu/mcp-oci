"""
Unified OCI MCP Server

Combines ALL tools from all OCI MCP servers into a single server for agent access.
Run with: python -m mcp_servers.unified.server
"""

from .server import app, all_tools

__all__ = ['app', 'all_tools']
