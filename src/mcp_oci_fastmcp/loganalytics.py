"""FastMCP Server: OCI Log Analytics (Optimized for Claude)

Auto-discovers namespace, provides clear responses for Claude.
No manual namespace parameters needed!
"""

import sys
from typing import Any, Dict, List, Optional

try:
    from fastmcp import FastMCP
except ImportError:
    print("fastmcp not available. Install with: pip install fastmcp", file=sys.stderr)
    sys.exit(1)

from mcp_oci_loganalytics.server_simple import (
    run_query_simple as run_query,
    list_entities_simple as list_entities,
    get_namespace_info_simple as get_namespace_info,
)


def run_loganalytics(profile: Optional[str] = None, region: Optional[str] = None, server_name: str = "oci-loganalytics-fast"):
    """Run the optimized Log Analytics FastMCP server with auto-namespace discovery."""
    app = FastMCP(server_name)

    def _with_defaults(kwargs):
        if profile and "profile" not in kwargs:
            kwargs["profile"] = profile
        if region and "region" not in kwargs:
            kwargs["region"] = region
        return kwargs

    @app.tool()
    async def oci_loganalytics_get_namespace(
        profile: str = None,
        region: str = None,
    ):
        """Get Log Analytics namespace information - auto-discovered! No parameters needed."""
        args = {
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return get_namespace_info(**args)

    @app.tool()
    async def oci_loganalytics_run_query(
        query_string: str,
        time_start: str,
        time_end: str,
        subsystem: str = None,
        max_total_count: int = None,
        profile: str = None,
        region: str = None,
    ):
        """Run a Log Analytics query - namespace auto-discovered! No namespace parameter needed."""
        args = {
            "query_string": query_string,
            "time_start": time_start,
            "time_end": time_end,
            "subsystem": subsystem,
            "max_total_count": max_total_count,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return run_query(**args)

    @app.tool()
    async def oci_loganalytics_list_entities(
        compartment_id: str,
        limit: int = None,
        page: str = None,
        profile: str = None,
        region: str = None,
    ):
        """List Log Analytics entities - namespace auto-discovered! Only compartment_id needed."""
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_entities(**args)


    @app.tool()
    async def get_server_info():
        return {
            "name": server_name,
            "framework": "fastmcp",
            "service": "loganalytics",
            "optimized": True,
            "features": [
                "Auto-discovers namespace - no manual parameters needed",
                "Clear, Claude-friendly responses",
                "Simplified API - only compartment_id required for most operations",
                "Better error handling and user guidance"
            ],
            "defaults": {"profile": profile, "region": region},
        }

    app.run()
