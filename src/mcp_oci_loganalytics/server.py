"""MCP Server: OCI Log Analytics (logan-api-spec 20200601)

Tools are exposed as `oci:loganalytics:<action>`.
Focus on query execution and common catalog listings.
"""

from typing import Any, Dict, List, Optional
from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: Optional[str] = None, region: Optional[str] = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.log_analytics.LogAnalyticsClient, profile=profile, region=region)


def _extract_items_from_response(resp) -> List[Any]:
    """Extract items from OCI response, handling both direct data and data.items patterns"""
    data = getattr(resp, "data", None)
    if data and hasattr(data, "items"):
        return [getattr(i, "__dict__", i) for i in data.items]
    else:
        return [getattr(i, "__dict__", i) for i in getattr(resp, "data", [])]


def register_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "oci:loganalytics:run-query",
            "description": "Run a Log Analytics query for a namespace and time range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "query_string": {"type": "string"},
                    "time_start": {"type": "string", "description": "ISO8601"},
                    "time_end": {"type": "string", "description": "ISO8601"},
                    "subsystem": {"type": "string", "description": "Optional subsystem filter"},
                    "max_total_count": {"type": "integer", "description": "Optional cap on rows"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "query_string", "time_start", "time_end"],
            },
            "handler": run_query,
        },
        {
            "name": "oci:loganalytics:list-entities",
            "description": "List Log Analytics entities for a namespace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "compartment_id"],
            },
            "handler": list_entities,
        },
        {
            "name": "oci:loganalytics:list-parsers",
            "description": "List parsers for a namespace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name"],
            },
            "handler": list_parsers,
        },
        {
            "name": "oci:loganalytics:list-log-groups",
            "description": "List log groups for a namespace (if supported).",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "compartment_id"],
            },
            "handler": list_log_groups,
        },
        {
            "name": "oci:loganalytics:list-saved-searches",
            "description": "List saved searches in a namespace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name"],
            },
            "handler": list_saved_searches,
        },
        {
            "name": "oci:loganalytics:list-scheduled-tasks",
            "description": "List scheduled tasks in a namespace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "compartment_id"],
            },
            "handler": list_scheduled_tasks,
        },
        {
            "name": "oci:loganalytics:upload-lookup",
            "description": "Upload a Lookup (CSV) to Log Analytics. Requires confirm=true; supports dry_run.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "name": {"type": "string"},
                    "file_path": {"type": "string"},
                    "description": {"type": "string"},
                    "type": {"type": "string", "enum": ["CSV", "JSON", "UNKNOWN"], "default": "CSV"},
                    "confirm": {"type": "boolean", "default": False},
                    "dry_run": {"type": "boolean", "default": False},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "name", "file_path"],
            },
            "handler": upload_lookup,
            "mutating": True,
        },
        {
            "name": "oci:loganalytics:list-work-requests",
            "description": "List work requests for a compartment and namespace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "namespace_name": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "namespace_name"],
            },
            "handler": list_work_requests,
        },
        {
            "name": "oci:loganalytics:get-work-request",
            "description": "Get a work request by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "work_request_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["work_request_id"],
            },
            "handler": get_work_request,
        },
        {
            "name": "oci:loganalytics:run-snippet",
            "description": "Run a convenience query snippet by name with parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "snippet": {"type": "string"},
                    "params": {"type": "object"},
                    "time_start": {"type": "string"},
                    "time_end": {"type": "string"},
                    "max_total_count": {"type": "integer"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "snippet", "time_start", "time_end"],
            },
            "handler": run_snippet,
        },
        {
            "name": "oci:loganalytics:list-snippets",
            "description": "List available convenience query snippet names.",
            "parameters": {"type": "object", "properties": {}},
            "handler": list_snippets,
        },
    ]


def _coerce_model(module: Any, candidates: List[str], payload: Dict[str, Any]) -> Any:
    last_err: Optional[Exception] = None
    for name in candidates:
        try:
            cls = getattr(module, name)
            return cls(**payload)
        except Exception as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    raise RuntimeError("No suitable model found for payload")


def run_query(namespace_name: str, query_string: str, time_start: str, time_end: str,
              subsystem: Optional[str] = None, max_total_count: Optional[int] = None,
              profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    client = create_client(profile=profile, region=region)
    # Build details payload
    details: Dict[str, Any] = {
        "query_string": query_string,
        "time_start": time_start,
        "time_end": time_end,
    }
    if subsystem:
        details["subsystem"] = subsystem
    if max_total_count is not None:
        details["max_total_count"] = max_total_count

    # Try known model names for the body
    model_module = oci.log_analytics.models
    model = _coerce_model(
        model_module,
        [
            "QueryBody",  # likely
            "QueryDetails",
            "SearchDetails",
            "SearchLogsDetails",
        ],
        details,
    )

    # Try possible method names
    candidates = [
        ("query", {"namespace_name": namespace_name, "query_details": model}),
        ("search", {"namespace_name": namespace_name, "search_details": model}),
        ("search_logs", {"namespace_name": namespace_name, "search_logs_details": model}),
        ("run_query", {"namespace_name": namespace_name, "query_body": model}),
    ]
    last_err: Optional[Exception] = None
    for method_name, kwargs in candidates:
        method = getattr(client, method_name, None)
        if method is None:
            continue
        try:
            resp = method(**kwargs)
            data = getattr(resp, "data", None)
            # Try common fields
            if data is None:
                return {"result": None}
            if hasattr(data, "items"):
                return with_meta(resp, {"items": [getattr(i, "__dict__", i) for i in data.items]})
            return with_meta(resp, {"result": getattr(data, "__dict__", data)})
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Failed to run query; last error: {last_err}")


def list_entities(namespace_name: str, compartment_id: str, limit: Optional[int] = None,
                  page: Optional[str] = None, profile: Optional[str] = None,
                  region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {"namespace_name": namespace_name, "compartment_id": compartment_id}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    # Try entity list methods
    candidates = ["list_log_analytics_entities", "list_entities"]
    for name in candidates:
        method = getattr(client, name, None)
        if method is None:
            continue
        resp = method(**kwargs)
        items = _extract_items_from_response(resp)
        next_page = getattr(resp, "opc_next_page", None)
        return with_meta(resp, {"items": items}, next_page=next_page)
    raise RuntimeError("No list entities method available in SDK")


def list_parsers(namespace_name: str, limit: Optional[int] = None, page: Optional[str] = None,
                 profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {"namespace_name": namespace_name}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    method = getattr(client, "list_parsers", None)
    if method is None:
        raise RuntimeError("list_parsers not available in this SDK version")
    resp = method(**kwargs)
    items = _extract_items_from_response(resp)
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_log_groups(namespace_name: str, compartment_id: str, limit: Optional[int] = None,
                    page: Optional[str] = None, profile: Optional[str] = None,
                    region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {"namespace_name": namespace_name, "compartment_id": compartment_id}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    # Some SDKs may not expose log groups; attempt a likely method
    candidates = ["list_log_groups", "list_log_analytics_log_groups"]
    for name in candidates:
        method = getattr(client, name, None)
        if method is None:
            continue
        resp = method(**kwargs)
        items = _extract_items_from_response(resp)
        next_page = getattr(resp, "opc_next_page", None)
        return {"items": items, "next_page": next_page}
    raise RuntimeError("Log group listing not available in this SDK version")


def list_saved_searches(namespace_name: str, limit: Optional[int] = None, page: Optional[str] = None,
                        profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {"namespace_name": namespace_name}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    candidates = ["list_saved_searches", "list_log_analytics_saved_searches"]
    for name in candidates:
        method = getattr(client, name, None)
        if method is None:
            continue
        resp = method(**kwargs)
        items = _extract_items_from_response(resp)
        next_page = getattr(resp, "opc_next_page", None)
        return {"items": items, "next_page": next_page}
    raise RuntimeError("Saved searches listing not available in this SDK version")


def list_scheduled_tasks(namespace_name: str, compartment_id: str, limit: Optional[int] = None,
                         page: Optional[str] = None, profile: Optional[str] = None,
                         region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {"namespace_name": namespace_name, "compartment_id": compartment_id}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    candidates = ["list_scheduled_tasks", "list_log_analytics_scheduled_tasks"]
    for name in candidates:
        method = getattr(client, name, None)
        if method is None:
            continue
        resp = method(**kwargs)
        items = _extract_items_from_response(resp)
        next_page = getattr(resp, "opc_next_page", None)
        return {"items": items, "next_page": next_page}
    raise RuntimeError("Scheduled tasks listing not available in this SDK version")


def upload_lookup(namespace_name: str, name: str, file_path: str, description: Optional[str] = None,
                  type: str = "CSV", confirm: bool = False, dry_run: bool = False,
                  profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    import os
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    if dry_run:
        return {"dry_run": True, "request": {"namespace_name": namespace_name, "name": name, "file_path": file_path, "description": description, "type": type}}
    if not os.path.exists(file_path):
        raise RuntimeError(f"File not found: {file_path}")
    client = create_client(profile=profile, region=region)
    # Possible method names
    candidates = ["upload_lookup", "upload_lookup_file", "put_lookup"]
    last_err: Optional[Exception] = None
    for method_name in candidates:
        method = getattr(client, method_name, None)
        if method is None:
            continue
        try:
            with open(file_path, "rb") as f:
                resp = method(namespace_name=namespace_name, name=name, upload_lookup_file_body=f, description=description)  # type: ignore
            data = getattr(resp, "data", None)
            return with_meta(resp, {"result": getattr(data, "__dict__", data)})
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Lookup upload not supported in this SDK version; last error: {last_err}")


def list_work_requests(compartment_id: str, namespace_name: str, limit: Optional[int] = None,
                       page: Optional[str] = None, profile: Optional[str] = None,
                       region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: Dict[str, Any] = {"compartment_id": compartment_id, "namespace_name": namespace_name}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    candidates = ["list_work_requests"]
    for name in candidates:
        method = getattr(client, name, None)
        if method is None:
            continue
        resp = method(**kwargs)
        items = _extract_items_from_response(resp)
        next_page = getattr(resp, "opc_next_page", None)
        return with_meta(resp, {"items": items}, next_page=next_page)
    raise RuntimeError("Work requests listing not available in this SDK version")


def get_work_request(work_request_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)
    method = getattr(client, "get_work_request", None)
    if method is None:
        raise RuntimeError("get_work_request not available in this SDK version")
    resp = method(work_request_id)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})


def run_snippet(namespace_name: str, snippet: str, params: Optional[Dict[str, Any]] = None,
                time_start: str = "", time_end: str = "", max_total_count: Optional[int] = None,
                profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    from .queries import render_snippet
    query_string = render_snippet(snippet, params or {})
    return run_query(namespace_name=namespace_name, query_string=query_string,
                     time_start=time_start, time_end=time_end, max_total_count=max_total_count,
                     profile=profile, region=region)


def list_snippets() -> Dict[str, Any]:
    from .queries import SNIPPETS
    return {"snippets": sorted(SNIPPETS.keys())}
