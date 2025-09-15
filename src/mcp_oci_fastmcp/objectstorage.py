from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_objectstorage(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-objectstorage-fast") -> None:
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )
    from mcp_oci_objectstorage.server import (
        list_buckets,
        get_bucket,
        list_objects,
        head_object,
        get_namespace,
        list_preauth_requests,
        create_preauth_request,
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
    async def oci_objectstorage_list_buckets(namespace_name: str, compartment_id: str, limit: int = None, page: str = None,
                                             profile: str = None, region: str = None):
        return list_buckets(**_with_defaults(locals()))

    @app.tool()
    async def oci_objectstorage_get_bucket(namespace_name: str, bucket_name: str, profile: str = None, region: str = None):
        return get_bucket(**_with_defaults(locals()))

    @app.tool()
    async def oci_objectstorage_list_objects(namespace_name: str, bucket_name: str, prefix: str = None,
                                             limit: int = None, page: str = None,
                                             profile: str = None, region: str = None):
        return list_objects(**_with_defaults(locals()))

    @app.tool()
    async def oci_objectstorage_head_object(namespace_name: str, bucket_name: str, object_name: str,
                                            profile: str = None, region: str = None):
        return head_object(**_with_defaults(locals()))

    @app.tool()
    async def oci_objectstorage_get_namespace(compartment_id: str = None, profile: str = None, region: str = None):
        return get_namespace(**_with_defaults(locals()))

    @app.tool()
    async def oci_objectstorage_list_preauth_requests(namespace_name: str, bucket_name: str, object_name: str = None,
                                                      limit: int = None, page: str = None,
                                                      profile: str = None, region: str = None):
        return list_preauth_requests(**_with_defaults(locals()))

    @app.tool()
    async def oci_objectstorage_create_preauth_request(namespace_name: str, bucket_name: str, name: str, access_type: str,
                                                       time_expires: str, object_name: str = None,
                                                       profile: str = None, region: str = None):
        return create_preauth_request(**_with_defaults(locals()))

    @app.tool()
    async def get_server_info():
        return {"name": server_name, "framework": "fastmcp", "service": "objectstorage", "defaults": {"profile": profile, "region": region}}

    app.run()
