"""Fast OCI Log Analytics MCP Server

This module provides a fast, reliable Log Analytics solution with:
- Direct REST API connections
- Fast query execution
- Reliable error handling
- Performance monitoring
- Optimized for speed and reliability
"""

from .server import register_tools, create_client, execute_query_fast, list_sources_fast, get_log_sources_last_days

__all__ = ["register_tools", "create_client", "execute_query_fast", "list_sources_fast", "get_log_sources_last_days"]
