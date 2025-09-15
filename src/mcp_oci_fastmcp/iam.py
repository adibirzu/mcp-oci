from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_iam(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-iam-fast") -> None:
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )
    from mcp_oci_iam.server_optimized import (
        list_users,
        get_user,
        list_compartments,
        list_groups,
        list_policies,
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
    async def oci_iam_list_users(compartment_id: str, name: str = None, limit: int = None, page: str = None,
                                 profile: str = None, region: str = None):
        args = {
            "compartment_id": compartment_id,
            "name": name,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_users(**args)

    @app.tool()
    async def oci_iam_get_user(user_id: str, profile: str = None, region: str = None):
        args = {
            "user_id": user_id,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return get_user(**args)

    @app.tool()
    async def oci_iam_list_compartments(compartment_id: str, include_subtree: bool = True, access_level: str = "ANY",
                                        limit: int = None, page: str = None,
                                        profile: str = None, region: str = None):
        args = {
            "compartment_id": compartment_id,
            "include_subtree": include_subtree,
            "access_level": access_level,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_compartments(**args)

    @app.tool()
    async def oci_iam_list_groups(compartment_id: str, limit: int = None, page: str = None,
                                  profile: str = None, region: str = None):
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_groups(**args)

    @app.tool()
    async def oci_iam_list_policies(compartment_id: str, limit: int = None, page: str = None,
                                    profile: str = None, region: str = None):
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_policies(**args)


    @app.tool()
    async def get_server_info():
        return {
            "name": server_name, 
            "framework": "fastmcp", 
            "service": "iam",
            "optimized": True,
            "features": [
                "Clear, Claude-friendly responses",
                "Structured data with helpful messages",
                "Better error handling and user guidance",
                "Consistent response format across all tools"
            ],
            "defaults": {"profile": profile, "region": region}
        }

    app.run()