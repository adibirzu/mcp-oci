from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_oke(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-oke-fast") -> None:
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )
    from mcp_oci_oke.server import (
        list_clusters,
        get_cluster,
        get_node_pool,
        list_node_pools,
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
    async def oci_oke_list_clusters(compartment_id: str, name: str = None, lifecycle_state: str = None,
                                    limit: int = None, page: str = None,
                                    profile: str = None, region: str = None):
        return list_clusters(**_with_defaults(locals()))

    @app.tool()
    async def oci_oke_get_cluster(cluster_id: str, profile: str = None, region: str = None):
        return get_cluster(**_with_defaults(locals()))

    @app.tool()
    async def oci_oke_get_node_pool(node_pool_id: str, profile: str = None, region: str = None):
        return get_node_pool(**_with_defaults(locals()))

    @app.tool()
    async def oci_oke_list_node_pools(compartment_id: str, cluster_id: str, name: str = None,
                                      limit: int = None, page: str = None,
                                      profile: str = None, region: str = None):
        return list_node_pools(**_with_defaults(locals()))

    @app.tool()
    async def get_server_info():
        return {"name": server_name, "framework": "fastmcp", "service": "oke", "defaults": {"profile": profile, "region": region}}

    app.run()
