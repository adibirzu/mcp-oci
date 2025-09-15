from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_blockstorage(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-blockstorage-fast") -> None:
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )
    from mcp_oci_blockstorage.server import (
        list_volumes,
        get_volume,
        list_volume_backups,
        get_volume_backup,
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
    async def oci_blockstorage_list_volumes(compartment_id: str, availability_domain: str = None,
                                            display_name: str = None, lifecycle_state: str = None,
                                            limit: int = None, page: str = None,
                                            profile: str = None, region: str = None):
        return list_volumes(**_with_defaults(locals()))

    @app.tool()
    async def oci_blockstorage_get_volume(volume_id: str, profile: str = None, region: str = None):
        return get_volume(**_with_defaults(locals()))

    @app.tool()
    async def oci_blockstorage_list_volume_backups(compartment_id: str, volume_id: str = None,
                                                   display_name: str = None, lifecycle_state: str = None,
                                                   limit: int = None, page: str = None,
                                                   profile: str = None, region: str = None):
        return list_volume_backups(**_with_defaults(locals()))

    @app.tool()
    async def oci_blockstorage_get_volume_backup(volume_backup_id: str, profile: str = None, region: str = None):
        return get_volume_backup(**_with_defaults(locals()))

    @app.tool()
    async def get_server_info():
        return {"name": server_name, "framework": "fastmcp", "service": "blockstorage", "defaults": {"profile": profile, "region": region}}

    app.run()
