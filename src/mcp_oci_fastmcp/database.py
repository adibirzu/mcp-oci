from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_database(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-database-fast") -> None:
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )
    from mcp_oci_database.server import (
        list_autonomous_databases,
        list_db_systems,
        list_backups,
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
    async def oci_database_list_autonomous_databases(compartment_id: str, lifecycle_state: str = None,
                                                     limit: int = None, page: str = None,
                                                     profile: str = None, region: str = None):
        return list_autonomous_databases(**_with_defaults(locals()))

    @app.tool()
    async def oci_database_list_db_systems(compartment_id: str, lifecycle_state: str = None,
                                           limit: int = None, page: str = None,
                                           profile: str = None, region: str = None):
        return list_db_systems(**_with_defaults(locals()))

    @app.tool()
    async def oci_database_list_backups(compartment_id: str, db_system_id: str = None, database_id: str = None,
                                        limit: int = None, page: str = None,
                                        profile: str = None, region: str = None):
        return list_backups(**_with_defaults(locals()))

    @app.tool()
    async def get_server_info():
        return {"name": server_name, "framework": "fastmcp", "service": "database", "defaults": {"profile": profile, "region": region}}

    app.run()
