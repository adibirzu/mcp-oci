"""Robust OCI Log Analytics MCP Server

This module provides a fast, reliable Log Analytics solution with:
- Optimized REST API connections
- Fast query execution
- Reliable error handling
- Performance monitoring
- Direct OCI SDK integration
"""

from .server import register_tools, create_client, RobustLogAnalyticsClient

__all__ = ["register_tools", "create_client", "RobustLogAnalyticsClient"]
