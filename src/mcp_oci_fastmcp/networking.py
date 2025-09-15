from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_networking(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-networking-fast") -> None:
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )
    from mcp_oci_networking.server import (
        list_vcns,
        list_subnets,
        list_route_tables,
        list_security_lists,
        list_nsgs,
        list_vcns_by_dns,
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
    async def oci_networking_list_vcns(compartment_id: str, limit: int = None, page: str = None,
                                       profile: str = None, region: str = None):
        return list_vcns(**_with_defaults(locals()))

    @app.tool()
    async def oci_networking_list_vcns_by_dns(compartment_id: str, dns_label: str, limit: int = None, page: str = None,
                                              profile: str = None, region: str = None):
        return list_vcns_by_dns(**_with_defaults(locals()))

    @app.tool()
    async def oci_networking_list_subnets(compartment_id: str, vcn_id: str = None,
                                          limit: int = None, page: str = None,
                                          profile: str = None, region: str = None):
        return list_subnets(**_with_defaults(locals()))

    @app.tool()
    async def oci_networking_list_route_tables(compartment_id: str, vcn_id: str = None,
                                               limit: int = None, page: str = None,
                                               profile: str = None, region: str = None):
        return list_route_tables(**_with_defaults(locals()))

    @app.tool()
    async def oci_networking_list_security_lists(compartment_id: str, vcn_id: str = None,
                                                 limit: int = None, page: str = None,
                                                 profile: str = None, region: str = None):
        return list_security_lists(**_with_defaults(locals()))

    @app.tool()
    async def oci_networking_list_nsgs(compartment_id: str, vcn_id: str = None, limit: int = None, page: str = None,
                                       profile: str = None, region: str = None):
        return list_nsgs(**_with_defaults(locals()))

    @app.tool()
    async def get_server_info():
        return {"name": server_name, "framework": "fastmcp", "service": "networking", "defaults": {"profile": profile, "region": region}}

    app.run()
