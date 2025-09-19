"""Compatibility shim for legacy imports.

Exposes a minimal API expected by older tests/integration code by delegating
to the consolidated implementation in mcp_servers.loganalytics.server.

Note: The canonical MCP server to use in clients is oci-mcp-observability
(mcp_servers/observability/server.py), which includes oci:loganalytics:* tools.
"""
from typing import Any


def run_query(
    namespace_name: str,
    query_string: str,
    time_start: str,
    time_end: str,
    subsystem: str | None = None,
    max_total_count: int | None = None,
    profile: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    from mcp_servers.loganalytics.server import run_query_legacy

    return run_query_legacy(
        namespace_name=namespace_name,
        query_string=query_string,
        time_start=time_start,
        time_end=time_end,
        subsystem=subsystem,
        max_total_count=max_total_count,
        profile=profile,
        region=region,
    )

