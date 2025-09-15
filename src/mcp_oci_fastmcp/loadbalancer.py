from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_loadbalancer(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-loadbalancer-fast") -> None:
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )
    from mcp_oci_loadbalancer.server import (
        list_load_balancers,
        get_backend_health,
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
    async def oci_loadbalancer_list_load_balancers(compartment_id: str, limit: int = None, page: str = None,
                                                   profile: str = None, region: str = None):
        return list_load_balancers(**_with_defaults(locals()))

    @app.tool()
    async def oci_loadbalancer_get_backend_health(load_balancer_id: str, backend_set_name: str,
                                                  profile: str = None, region: str = None):
        return get_backend_health(**_with_defaults(locals()))

    @app.tool()
    async def get_server_info():
        return {"name": server_name, "framework": "fastmcp", "service": "loadbalancer", "defaults": {"profile": profile, "region": region}}

    app.run()
