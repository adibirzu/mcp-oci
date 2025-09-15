from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_compute(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-compute-fast") -> None:
    """Serve a minimal FastMCP app that wraps compute tools.

    This is an optional FastMCP-based server. It registers a focused set of
    tools useful for common tasks and delegates to the existing SDK handlers.
    """
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )

    # Lazy import to avoid SDK requirement on module import
    from mcp_oci_compute.server import (
        list_instances,
        search_instances,
        list_stopped_instances,
    )

    app = FastMCP(server_name)

    def _with_defaults(kwargs):
        if profile and "profile" not in kwargs:
            kwargs["profile"] = profile
        if region and "region" not in kwargs:
            kwargs["region"] = region
        # Remove any function names that might be in locals()
        for key in list(kwargs.keys()):
            if key.startswith('oci_compute_') or key == '_with_defaults':
                kwargs.pop(key, None)
        return kwargs

    @app.tool()
    async def oci_compute_list_instances(
        compartment_id: str = None,
        compartment_name: str = None,
        lifecycle_state: str = None,
        include_subtree: bool = True,
        display_name: str = None,
        display_name_contains: str = None,
        shape: str = None,
        time_created_after: str = None,
        time_created_before: str = None,
        limit: int = None,
        page: str = None,
        max_items: int = None,
        profile: str = None,
        region: str = None,
    ):
        # Build args dict manually to avoid function name in locals()
        args = {
            "compartment_id": compartment_id,
            "compartment_name": compartment_name,
            "lifecycle_state": lifecycle_state,
            "include_subtree": include_subtree,
            "display_name": display_name,
            "display_name_contains": display_name_contains,
            "shape": shape,
            "time_created_after": time_created_after,
            "time_created_before": time_created_before,
            "limit": limit,
            "page": page,
            "max_items": max_items,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_instances(**args)

    @app.tool()
    async def oci_compute_search_instances(
        query: str = None,
        lifecycle_state: str = None,
        display_name: str = None,
        compartment_id: str = None,
        include_subtree: bool = True,
        limit: int = None,
        page: str = None,
        profile: str = None,
        region: str = None,
    ):
        args = {
            "query": query,
            "lifecycle_state": lifecycle_state,
            "display_name": display_name,
            "compartment_id": compartment_id,
            "include_subtree": include_subtree,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return search_instances(**args)

    @app.tool()
    async def oci_compute_list_stopped_instances(
        compartment_id: str = None,
        compartment_name: str = None,
        include_subtree: bool = True,
        display_name: str = None,
        display_name_contains: str = None,
        shape: str = None,
        time_created_after: str = None,
        time_created_before: str = None,
        limit: int = None,
        page: str = None,
        max_items: int = None,
        profile: str = None,
        region: str = None,
    ):
        args = {
            "compartment_id": compartment_id,
            "compartment_name": compartment_name,
            "include_subtree": include_subtree,
            "display_name": display_name,
            "display_name_contains": display_name_contains,
            "shape": shape,
            "time_created_after": time_created_after,
            "time_created_before": time_created_before,
            "limit": limit,
            "page": page,
            "max_items": max_items,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_stopped_instances(**args)

    @app.tool()
    async def get_server_info():
        return {
            "name": server_name,
            "framework": "fastmcp",
            "service": "compute",
            "defaults": {"profile": profile, "region": region},
        }

    app.run()