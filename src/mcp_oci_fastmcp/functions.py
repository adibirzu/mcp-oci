from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_functions(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-functions-fast") -> None:
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )
    from mcp_oci_functions.server import (
        list_applications,
        list_functions,
        get_application,
        get_function,
        list_triggers,
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
    async def oci_functions_list_applications(compartment_id: str, display_name: str = None,
                                              limit: int = None, page: str = None,
                                              profile: str = None, region: str = None):
        return list_applications(**_with_defaults(locals()))

    @app.tool()
    async def oci_functions_list_functions(application_id: str, display_name: str = None,
                                           limit: int = None, page: str = None,
                                           profile: str = None, region: str = None):
        return list_functions(**_with_defaults(locals()))

    @app.tool()
    async def oci_functions_get_application(application_id: str, profile: str = None, region: str = None):
        return get_application(**_with_defaults(locals()))

    @app.tool()
    async def oci_functions_get_function(function_id: str, profile: str = None, region: str = None):
        return get_function(**_with_defaults(locals()))

    @app.tool()
    async def oci_functions_list_triggers(application_id: str, profile: str = None, region: str = None):
        return list_triggers(**_with_defaults(locals()))

    @app.tool()
    async def get_server_info():
        return {"name": server_name, "framework": "fastmcp", "service": "functions", "defaults": {"profile": profile, "region": region}}

    app.run()
