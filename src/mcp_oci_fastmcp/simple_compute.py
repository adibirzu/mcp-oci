from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_simple_compute(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-compute-simple") -> None:
    """Serve a minimal FastMCP app that wraps compute tools with simple types."""
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
        # Remove the _with_defaults key if it exists
        kwargs.pop("_with_defaults", None)
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
        args = _with_defaults(locals())
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
        args = _with_defaults(locals())
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
        args = _with_defaults(locals())
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
