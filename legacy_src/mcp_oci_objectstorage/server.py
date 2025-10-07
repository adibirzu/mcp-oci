"""MCP Server: OCI Object Storage

Tools as `oci:objectstorage:<action>`.
"""

from typing import Any

from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta
from mcp_oci_common.cache import get_cache
from mcp_oci_common.name_registry import get_registry
from mcp_oci_common.observability import init_tracing, tool_span, add_oci_call_attributes

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.object_storage.ObjectStorageClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci_objectstorage_list_buckets",
            "description": "List buckets in a namespace/compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "compartment_id"],
            },
            "handler": list_buckets,
        },
        {
            "name": "oci_objectstorage_get_namespace",
            "description": "Get object storage namespace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
            },
            "handler": get_namespace,
        },
        {
            "name": "oci_objectstorage_list_objects",
            "description": "List objects in a bucket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "bucket_name": {"type": "string"},
                    "prefix": {"type": "string"},
                    "start": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "bucket_name"],
            },
            "handler": list_objects,
        },
        {
            "name": "oci_objectstorage_get_bucket",
            "description": "Get bucket details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "bucket_name": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "bucket_name"],
            },
            "handler": get_bucket,
        },
        {
            "name": "oci_objectstorage_list_preauth_requests",
            "description": "List preauthenticated requests for a bucket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "bucket_name": {"type": "string"},
                    "object_name": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "bucket_name"],
            },
            "handler": list_preauth_requests,
        },
        {
            "name": "oci_objectstorage_create_preauth_request",
            "description": "Create a preauthenticated request (requires confirm=true; supports dry_run).",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "bucket_name": {"type": "string"},
                    "name": {"type": "string"},
                    "access_type": {"type": "string"},
                    "time_expires": {"type": "string", "description": "ISO8601 timestamp"},
                    "object_name": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": False},
                    "confirm": {"type": "boolean", "default": False},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "bucket_name", "name", "access_type", "time_expires"],
            },
            "handler": create_preauth_request,
            "mutating": True,
        },
        {
            "name": "oci_objectstorage_head_object",
            "description": "Get object metadata (HEAD).",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "bucket_name": {"type": "string"},
                    "object_name": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "bucket_name", "object_name"],
            },
            "handler": head_object,
        },
    ]


def list_buckets(namespace_name: str, compartment_id: str, limit: int | None = None,
                 page: str | None = None, profile: str | None = None,
                 region: str | None = None) -> dict[str, Any]:
    tracer = init_tracing("mcp-oci-objectstorage")
    with tool_span(tracer, "oci_objectstorage_list_buckets", mcp_server="oci-mcp-objectstorage") as span:
        client = create_client(profile=profile, region=region)
    cache = get_cache()
    registry = get_registry()
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    cache_params = {"namespace_name": namespace_name, "compartment_id": compartment_id, "limit": limit, "page": page}
    cached = cache.get("objectstorage", "list_buckets", cache_params)
    if cached:
        return cached
    resp = client.list_buckets(namespace_name=namespace_name, compartment_id=compartment_id, **kwargs)
    try:
        add_oci_call_attributes(
            span,
            oci_service="objectstorage",
            oci_operation="ListBuckets",
            region=region,
            endpoint=getattr(client, "base_client", None).endpoint if hasattr(client, "base_client") else None,
            request_id=(getattr(resp, "headers", {}) or {}).get("opc-request-id") if hasattr(resp, "headers") else None,
        )
    except Exception:
        pass
    items = [b.__dict__ for b in getattr(resp, "data", [])]
    # Optional: record bucket names under applications_by_name map keyed by compartment
    if items:
        try:
            # Reuse applications_by_name as a generic name store for bucket names
            registry.update_applications(compartment_id, [{"id": f"bucket://{namespace_name}/{b.get('name')}", "display_name": b.get('name')} for b in items])
        except Exception:
            pass
    next_page = getattr(resp, "opc_next_page", None)
    out = with_meta(resp, {"items": items}, next_page=next_page)
    import os
    ttl = int(os.getenv("MCP_CACHE_TTL_OBJECTSTORAGE", os.getenv("MCP_CACHE_TTL", "1800")))
    cache.set("objectstorage", "list_buckets", cache_params, out, ttl_seconds=ttl)
    return out


def get_namespace(compartment_id: str | None = None, profile: str | None = None,
                  region: str | None = None) -> dict[str, Any]:
    tracer = init_tracing("mcp-oci-objectstorage")
    with tool_span(tracer, "oci_objectstorage_get_namespace", mcp_server="oci-mcp-objectstorage") as span:
        client = create_client(profile=profile, region=region)
    if compartment_id:
        resp = client.get_namespace(compartment_id=compartment_id)
    else:
        resp = client.get_namespace()
    ns = resp.data if hasattr(resp, "data") else resp
    try:
        add_oci_call_attributes(
            span,
            oci_service="objectstorage",
            oci_operation="GetNamespace",
            region=region,
            endpoint=getattr(client, "base_client", None).endpoint if hasattr(client, "base_client") else None,
            request_id=(getattr(resp, "headers", {}) or {}).get("opc-request-id") if hasattr(resp, "headers") else None,
        )
    except Exception:
        pass
    return with_meta(resp, {"namespace": ns})


def list_objects(namespace_name: str, bucket_name: str, prefix: str | None = None,
                 start: str | None = None, limit: int | None = None,
                 profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if prefix:
        kwargs["prefix"] = prefix
    if start:
        kwargs["start"] = start
    if limit:
        kwargs["limit"] = limit
    resp = client.list_objects(namespace_name=namespace_name, bucket_name=bucket_name, **kwargs)
    data = getattr(resp, "data", None)
    if data and hasattr(data, "objects"):
        items = [o.__dict__ for o in data.objects]
        next_start = getattr(data, "next_start_with", None)
        return with_meta(resp, {"items": items, "next_start_with": next_start})
    return with_meta(resp, {"items": []})


def get_bucket(namespace_name: str, bucket_name: str, profile: str | None = None,
               region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_bucket(namespace_name=namespace_name, bucket_name=bucket_name)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})


def head_object(namespace_name: str, bucket_name: str, object_name: str,
                profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.head_object(namespace_name=namespace_name, bucket_name=bucket_name, object_name=object_name)
    headers = getattr(resp, "headers", {})
    return with_meta(resp, {"item": dict(headers)})


def list_preauth_requests(namespace_name: str, bucket_name: str, object_name: str | None = None,
                          limit: int | None = None, page: str | None = None,
                          profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if object_name:
        kwargs["object_name"] = object_name
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_preauthenticated_requests(namespace_name=namespace_name, bucket_name=bucket_name, **kwargs)
    items = [r.__dict__ for r in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def create_preauth_request(namespace_name: str, bucket_name: str, name: str, access_type: str,
                           time_expires: str, object_name: str | None = None,
                           dry_run: bool = False, confirm: bool = False,
                           profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    details = {
        "name": name,
        "access_type": access_type,
        "time_expires": time_expires,
    }
    if object_name:
        details["object_name"] = object_name
    # Dry run support
    if dry_run:
        return {"dry_run": True, "request": details}
    # Build proper SDK model
    try:
        model = oci.object_storage.models.CreatePreauthenticatedRequestDetails(**details)  # type: ignore
    except Exception:
        # Fallback: some SDKs require camelCase keys; let SDK handle mapping when possible
        model = oci.object_storage.models.CreatePreauthenticatedRequestDetails(
            name=name, access_type=access_type, time_expires=time_expires, object_name=object_name
        )  # type: ignore
    client = create_client(profile=profile, region=region)
    resp = client.create_preauthenticated_request(namespace_name=namespace_name, bucket_name=bucket_name, create_preauthenticated_request_details=model)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})
