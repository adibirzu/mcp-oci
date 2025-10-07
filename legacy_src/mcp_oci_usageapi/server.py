"""MCP Server: OCI Usage API (Cost and Usage Analytics)

Exposes tools as `oci:usageapi:<action>`.
"""

from datetime import UTC
from typing import Any

from mcp_oci_common import make_client

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.usage_api.UsageapiClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci_usageapi_request_summarized_usages",
            "description": "Request summarized usage or cost between two timestamps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_id": {"type": "string"},
                    "time_usage_started": {"type": "string", "description": "ISO8601"},
                    "time_usage_ended": {"type": "string", "description": "ISO8601"},
                    "granularity": {
                        "type": "string",
                        "enum": ["DAILY", "MONTHLY"],
                        "default": "DAILY",
                    },
                    "query_type": {
                        "type": "string",
                        "enum": ["USAGE", "COST"],
                        "default": "COST",
                    },
                    "group_by": {"type": "array", "items": {"type": "string"}},
                    "dimensions": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": 'Optional server-side dimensions filter (e.g., {"service": "Compute"})',
                    },
                    "tags": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": "Optional server-side tags filter",
                    },
                    "compartment_id": {
                        "type": "string",
                        "description": "Optional: inject into dimensions as compartmentId",
                    },
                    "compartment_name": {
                        "type": "string",
                        "description": "Resolve to OCID and inject into dimensions as compartmentId",
                    },
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenant_id", "time_usage_started", "time_usage_ended"],
            },
            "handler": request_summarized_usages,
        },
        {
            "name": "oci_usageapi_cost_by_service",
            "description": "Convenience: Summarized COST grouped by service for the last N days (times normalized to midnight UTC). Optional client-side service filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_id": {"type": "string"},
                    "days": {"type": "integer", "minimum": 1, "default": 7},
                    "granularity": {
                        "type": "string",
                        "enum": ["DAILY", "MONTHLY"],
                        "default": "DAILY",
                    },
                    "service_name": {
                        "type": "string",
                        "description": "Optional client-side filter",
                    },
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenant_id"],
            },
            "handler": cost_by_service,
        },
        {
            "name": "oci_usageapi_cost_by_compartment",
            "description": "Convenience: Summarized COST grouped by compartmentId for last N days (midnight UTC). Optional client-side compartment filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_id": {"type": "string"},
                    "days": {"type": "integer", "minimum": 1, "default": 7},
                    "granularity": {
                        "type": "string",
                        "enum": ["DAILY", "MONTHLY"],
                        "default": "DAILY",
                    },
                    "compartment_id": {
                        "type": "string",
                        "description": "Optional client-side filter",
                    },
                    "compartment_name": {
                        "type": "string",
                        "description": "Resolve to OCID then filter client-side",
                    },
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenant_id"],
            },
            "handler": cost_by_compartment,
        },
        {
            "name": "oci_usageapi_usage_by_service",
            "description": "Convenience: Summarized USAGE grouped by service for last N days (midnight UTC). Optional service filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_id": {"type": "string"},
                    "days": {"type": "integer", "minimum": 1, "default": 7},
                    "granularity": {
                        "type": "string",
                        "enum": ["DAILY", "MONTHLY"],
                        "default": "DAILY",
                    },
                    "service_name": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenant_id"],
            },
            "handler": usage_by_service,
        },
        {
            "name": "oci_usageapi_usage_by_compartment",
            "description": "Convenience: Summarized USAGE grouped by compartmentId for last N days (midnight UTC). Optional compartment filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_id": {"type": "string"},
                    "days": {"type": "integer", "minimum": 1, "default": 7},
                    "granularity": {
                        "type": "string",
                        "enum": ["DAILY", "MONTHLY"],
                        "default": "DAILY",
                    },
                    "compartment_id": {"type": "string"},
                    "compartment_name": {
                        "type": "string",
                        "description": "Resolve to OCID then filter client-side",
                    },
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenant_id"],
            },
            "handler": usage_by_compartment,
        },
        {
            "name": "oci_usageapi_count_instances",
            "description": "Count compute instances in a compartment (by id or name). Includes subtree by default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "compartment_name": {"type": "string"},
                    "include_subtree": {"type": "boolean", "default": True},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
            },
            "handler": count_instances,
        },
        {
            "name": "oci_usageapi_correlate_costs_and_resources",
            "description": "Aggregate cost-by-service and resource counts (by resourceType) for correlation. Optionally scope to a compartment (id or name).",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_id": {"type": "string"},
                    "days": {"type": "integer", "minimum": 1, "default": 7},
                    "granularity": {
                        "type": "string",
                        "enum": ["DAILY", "MONTHLY"],
                        "default": "DAILY",
                    },
                    "compartment_id": {"type": "string"},
                    "compartment_name": {"type": "string"},
                    "include_subtree": {"type": "boolean", "default": True},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenant_id"],
            },
            "handler": correlate_costs_and_resources,
        },
        {
            "name": "oci_usageapi_showusage_run",
            "description": "Run Oracle showusage example tool and return its output (requires local clone).",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "ISO8601 start"},
                    "end": {"type": "string", "description": "ISO8601 end"},
                    "granularity": {
                        "type": "string",
                        "enum": ["DAILY", "MONTHLY"],
                        "default": "DAILY",
                    },
                    "groupby": {"type": "string", "description": "e.g., service"},
                    "extra_args": {
                        "type": "string",
                        "description": "additional CLI flags",
                    },
                    "expect_json": {"type": "boolean", "default": False},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                    "path": {
                        "type": "string",
                        "description": "Path to showusage.py (optional)",
                    },
                },
                "required": ["start", "end"],
            },
            "handler": showusage_run,
        },
        {
            "name": "oci_usageapi_list_rate_cards",
            "description": "List rate cards (list price) for a subscription.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subscription_id": {"type": "string"},
                    "time_from": {"type": "string", "description": "ISO8601; optional"},
                    "time_to": {"type": "string", "description": "ISO8601; optional"},
                    "part_number": {
                        "type": "string",
                        "description": "Optional product part number to filter client-side",
                    },
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["subscription_id"],
            },
            "handler": list_rate_cards,
        },
    ]


def request_summarized_usages(
    tenant_id: str,
    time_usage_started: str,
    time_usage_ended: str,
    granularity: str = "DAILY",
    query_type: str = "COST",
    group_by: list[str] | None = None,
    dimensions: dict[str, str] | None = None,
    tags: dict[str, str] | None = None,
    compartment_id: str | None = None,
    compartment_name: str | None = None,
    profile: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    client = create_client(profile=profile, region=region)
    # Normalize times to meet API precision requirements for DAILY/MONTHLY
    t_start = (
        _normalize_utc_midnight(time_usage_started)
        if granularity in ("DAILY", "MONTHLY")
        else time_usage_started
    )
    t_end = (
        _normalize_utc_midnight(time_usage_ended)
        if granularity in ("DAILY", "MONTHLY")
        else time_usage_ended
    )
    details = {
        "tenant_id": tenant_id,
        "time_usage_started": t_start,
        "time_usage_ended": t_end,
        "granularity": granularity,
        "query_type": query_type,
    }
    if group_by:
        details["group_by"] = group_by
    # Try to attach server-side filter model if provided
    if compartment_name and not compartment_id:
        # Resolve compartment name to OCID
        resolved = _resolve_compartment_name_to_id(
            compartment_name, profile=profile, region=region
        )
        if resolved:
            compartment_id = resolved
    # Merge compartment_id into dimensions if given
    if compartment_id:
        dimensions = {**(dimensions or {}), "compartmentId": compartment_id}
    if dimensions or tags:
        filt = _build_filter(dimensions or {}, tags or {})
        if filt is not None:
            details["filter"] = filt
    try:
        model = oci.usage_api.models.RequestSummarizedUsagesDetails(**details)  # type: ignore
    except Exception:
        # Fallback if field names differ; rely on SDK mapping
        model = oci.usage_api.models.RequestSummarizedUsagesDetails(
            tenant_id=tenant_id,
            time_usage_started=time_usage_started,
            time_usage_ended=time_usage_ended,
            granularity=granularity,
            query_type=query_type,
            group_by=group_by or None,
        )  # type: ignore
    resp = client.request_summarized_usages(request_summarized_usages_details=model)
    # Normalize response across SDK versions
    items: list[dict[str, Any]] = []
    if hasattr(resp, "data"):
        data = resp.data
        if isinstance(data, list):
            items = [getattr(i, "__dict__", i) for i in data]
        elif hasattr(data, "items"):
            try:
                items = [getattr(i, "__dict__", i) for i in data.items]
            except Exception:
                items = [getattr(data, "__dict__", data)]
        else:
            items = [getattr(data, "__dict__", data)]
    elif hasattr(resp, "items"):
        data_items = resp.items
        items = [getattr(i, "__dict__", i) for i in (data_items or [])]
    from mcp_oci_common.response import with_meta

    return with_meta(resp, {"items": items})


def cost_by_service(
    tenant_id: str,
    days: int = 7,
    granularity: str = "DAILY",
    service_name: str | None = None,
    profile: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    from datetime import datetime, timedelta

    today = datetime.now(UTC).date()
    end_dt = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    start_dt = end_dt - timedelta(days=days)
    result = request_summarized_usages(
        tenant_id=tenant_id,
        time_usage_started=start_dt.strftime("%Y-%m-%dT00:00:00Z"),
        time_usage_ended=end_dt.strftime("%Y-%m-%dT00:00:00Z"),
        granularity=granularity,
        query_type="COST",
        group_by=["service"],
        profile=profile,
        region=region,
    )
    if service_name and isinstance(result.get("items"), list):
        items = [i for i in result["items"] if str(i.get("service")) == service_name]
        result["items"] = items
    return result


def cost_by_compartment(
    tenant_id: str,
    days: int = 7,
    granularity: str = "DAILY",
    compartment_id: str | None = None,
    compartment_name: str | None = None,
    profile: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    from datetime import datetime, timedelta

    today = datetime.now(UTC).date()
    end_dt = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    start_dt = end_dt - timedelta(days=days)
    result = request_summarized_usages(
        tenant_id=tenant_id,
        time_usage_started=start_dt.strftime("%Y-%m-%dT00:00:00Z"),
        time_usage_ended=end_dt.strftime("%Y-%m-%dT00:00:00Z"),
        granularity=granularity,
        query_type="COST",
        group_by=["compartmentId"],
        compartment_id=compartment_id,
        compartment_name=compartment_name,
        profile=profile,
        region=region,
    )
    effective_compartment = compartment_id
    if not effective_compartment and compartment_name:
        effective_compartment = _resolve_compartment_name_to_id(
            compartment_name, profile=profile, region=region
        )
    if effective_compartment and isinstance(result.get("items"), list):
        items = [
            i
            for i in result["items"]
            if str(i.get("compartmentId")) == effective_compartment
        ]
        result["items"] = items
    return result


def usage_by_service(
    tenant_id: str,
    days: int = 7,
    granularity: str = "DAILY",
    service_name: str | None = None,
    profile: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    from datetime import datetime, timedelta

    today = datetime.now(UTC).date()
    end_dt = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    start_dt = end_dt - timedelta(days=days)
    result = request_summarized_usages(
        tenant_id=tenant_id,
        time_usage_started=start_dt.strftime("%Y-%m-%dT00:00:00Z"),
        time_usage_ended=end_dt.strftime("%Y-%m-%dT00:00:00Z"),
        granularity=granularity,
        query_type="USAGE",
        group_by=["service"],
        profile=profile,
        region=region,
    )
    if service_name and isinstance(result.get("items"), list):
        items = [i for i in result["items"] if str(i.get("service")) == service_name]
        result["items"] = items
    return result


def usage_by_compartment(
    tenant_id: str,
    days: int = 7,
    granularity: str = "DAILY",
    compartment_id: str | None = None,
    compartment_name: str | None = None,
    profile: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    from datetime import datetime, timedelta

    today = datetime.now(UTC).date()
    end_dt = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    start_dt = end_dt - timedelta(days=days)
    result = request_summarized_usages(
        tenant_id=tenant_id,
        time_usage_started=start_dt.strftime("%Y-%m-%dT00:00:00Z"),
        time_usage_ended=end_dt.strftime("%Y-%m-%dT00:00:00Z"),
        granularity=granularity,
        query_type="USAGE",
        group_by=["compartmentId"],
        compartment_id=compartment_id,
        compartment_name=compartment_name,
        profile=profile,
        region=region,
    )
    effective_compartment = compartment_id
    if not effective_compartment and compartment_name:
        effective_compartment = _resolve_compartment_name_to_id(
            compartment_name, profile=profile, region=region
        )
    if effective_compartment and isinstance(result.get("items"), list):
        items = [
            i
            for i in result["items"]
            if str(i.get("compartmentId")) == effective_compartment
        ]
        result["items"] = items
    return result


def _normalize_utc_midnight(ts: str) -> str:
    """Coerce a timestamp or date string to UTC midnight RFC3339 (YYYY-MM-DDT00:00:00Z)."""
    # Accept date-only (YYYY-MM-DD) or full datetime; always return midnight
    if len(ts) >= 10:
        date_part = ts[:10]
        return f"{date_part}T00:00:00Z"
    return ts


def _build_filter(dimensions: dict[str, str], tags: dict[str, str]):
    """Attempt to construct a Usage API filter model with dimensions/tags.
    Returns None if SDK model is unavailable or incompatible.
    """
    try:
        import oci  # type: ignore

        models = oci.usage_api.models
        # Some SDKs expect dicts for dimensions/tags; others expect complex structures.
        # We optimistically try Filter(operator="AND", dimensions=..., tags=...)
        kwargs: dict[str, Any] = {"operator": "AND"}
        if dimensions:
            kwargs["dimensions"] = dimensions
        if tags:
            kwargs["tags"] = tags
        return models.Filter(**kwargs)
    except Exception:
        return None


def list_rate_cards(
    subscription_id: str,
    time_from: str | None = None,
    time_to: str | None = None,
    part_number: str | None = None,
    profile: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {"subscription_id": subscription_id}
    if time_from:
        kwargs["time_from"] = _normalize_utc_midnight(time_from)
    if time_to:
        kwargs["time_to"] = _normalize_utc_midnight(time_to)
    method = getattr(client, "list_rate_cards", None)
    if method is None:
        raise RuntimeError("list_rate_cards not available in this SDK version")
    resp = method(**kwargs)
    items = [i.__dict__ for i in getattr(resp, "data", [])]
    if part_number:
        items = [i for i in items if str(i.get("partNumber")) == part_number]
    from mcp_oci_common.response import with_meta

    return with_meta(resp, {"items": items})


def showusage_run(
    start: str,
    end: str,
    granularity: str = "DAILY",
    groupby: str | None = None,
    extra_args: str | None = None,
    expect_json: bool = False,
    profile: str | None = None,
    region: str | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    import os
    import subprocess

    from mcp_oci_common.parsing import parse_json_loose, parse_kv_lines

    script = (
        path
        or os.environ.get("SHOWUSAGE_PATH")
        or "third_party/oci-python-sdk/examples/showusage/showusage.py"
    )
    if not os.path.exists(script):
        raise RuntimeError(
            "showusage.py not found; set SHOWUSAGE_PATH or place under third_party/.../showusage.py"
        )
    cmd = ["python", script, "-start", start, "-end", end, "-granularity", granularity]
    if groupby:
        cmd += ["-groupby", groupby]
    if extra_args:
        import shlex as _shlex

        cmd += _shlex.split(extra_args)
    if profile:
        cmd += ["-profile", profile]
    if region:
        cmd += ["-region", region]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"showusage failed: {proc.stderr.strip()}")
    result: dict[str, Any] = {"stdout": proc.stdout}
    if expect_json:
        parsed = parse_json_loose(proc.stdout)
        if parsed is None:
            parsed = parse_kv_lines(proc.stdout)
        result["parsed"] = parsed
    return result


# ---------------- Convenience helpers and correlation ----------------


def _resolve_compartment_name_to_id(
    name: str, *, profile: str | None, region: str | None
) -> str | None:
    """Resolve a compartment name to its OCID using the shared registry, populating it if needed.
    Falls back to Identity list_compartments with subtree traversal. Returns None if not found or on error.
    """
    try:
        from mcp_oci_common.name_registry import get_registry as _get_reg

        reg = _get_reg()
        ocid = reg.resolve_compartment(name)
        if ocid:
            return ocid
        # Build registry once
        _populate_compartment_registry(profile=profile, region=region)
        return reg.resolve_compartment(name)
    except Exception:
        return None


def _populate_compartment_registry(*, profile: str | None, region: str | None) -> None:
    try:
        if oci is None:
            return
        from mcp_oci_common import make_client as _make, get_oci_config as _get_cfg  # type: ignore

        cfg = _get_cfg(profile_name=profile)
        if region:
            cfg["region"] = region
        root = cfg.get("tenancy")
        if not root:
            return
        iam = _make(oci.identity.IdentityClient, profile=profile, region=region)
        items: list[dict] = [{"id": root, "name": "tenancy"}]
        nextp: str | None = None
        while True:
            kwargs_comp: dict[str, Any] = {
                "compartment_id": root,
                "compartment_id_in_subtree": True,
                "access_level": "ANY",
            }
            if nextp:
                kwargs_comp["page"] = nextp
            respc = iam.list_compartments(**kwargs_comp)
            for c in getattr(respc, "data", []) or []:
                items.append(
                    {
                        "id": getattr(c, "id", None),
                        "name": getattr(c, "name", None),
                    }
                )
            nextp = getattr(respc, "opc_next_page", None)
            if not nextp:
                break
        from mcp_oci_common.name_registry import get_registry as _get_reg

        _get_reg().update_compartments(items)
    except Exception:
        return


def count_instances(
    compartment_id: str | None = None,
    compartment_name: str | None = None,
    include_subtree: bool = True,
    profile: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Count compute instances using Resource Search for efficiency."""
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    # Resolve compartment name if needed
    if not compartment_id and compartment_name:
        compartment_id = (
            _resolve_compartment_name_to_id(
                compartment_name, profile=profile, region=region
            )
            or compartment_id
        )
    # Determine root compartment (tenancy) if nothing provided
    if not compartment_id:
        try:
            from mcp_oci_common import get_oci_config  # type: ignore

            cfg = get_oci_config(profile_name=profile)
            if region:
                cfg["region"] = region
            compartment_id = cfg.get("tenancy")
        except Exception:
            pass
    if not compartment_id:
        raise ValueError("compartment_id is required (no default tenancy found)")

    # Use Resource Search structured query: "query instance resources"
    rs_client = make_client(
        oci.resource_search.ResourceSearchClient, profile=profile, region=region
    )
    models = oci.resource_search.models
    query = "query instance resources"
    details = models.StructuredSearchDetails(query=query)
    total = 0
    page: str | None = None
    while True:
        kwargs: dict[str, Any] = {
            "search_details": details,
            "compartment_id": compartment_id,
            "compartment_id_in_subtree": include_subtree,
            "limit": 1000,
        }
        if page:
            kwargs["page"] = page
        resp = rs_client.search_resources(**kwargs)
        items = (
            getattr(resp.data, "items", [])
            if hasattr(resp, "data")
            else getattr(resp, "items", [])
        )
        total += len(items or [])
        page = getattr(resp, "opc_next_page", None)
        if not page:
            break
    return {
        "count": total,
        "resource": "instance",
        "compartment_id": compartment_id,
        "include_subtree": include_subtree,
    }


def correlate_costs_and_resources(
    tenant_id: str,
    days: int = 7,
    granularity: str = "DAILY",
    compartment_id: str | None = None,
    compartment_name: str | None = None,
    include_subtree: bool = True,
    profile: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Return cost-by-service and resource counts grouped by resourceType for correlation.
    Notes:
    - Resource counts use Resource Search across the specified scope.
    - Cost data uses Usage API grouped by service.
    """
    # Resolve compartment name if needed for both APIs
    effective_compartment = compartment_id
    if not effective_compartment and compartment_name:
        effective_compartment = _resolve_compartment_name_to_id(
            compartment_name, profile=profile, region=region
        )

    # Cost by service
    cost = cost_by_service(
        tenant_id=tenant_id,
        days=days,
        granularity=granularity,
        profile=profile,
        region=region,
    )

    # Resource counts by resourceType using Resource Search
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    rs_client = make_client(
        oci.resource_search.ResourceSearchClient, profile=profile, region=region
    )
    models = oci.resource_search.models
    query = "query all resources"
    details = models.StructuredSearchDetails(query=query)
    # Determine root scope
    scope_compartment = effective_compartment
    if not scope_compartment:
        try:
            from mcp_oci_common import get_oci_config  # type: ignore

            cfg = get_oci_config(profile_name=profile)
            if region:
                cfg["region"] = region
            scope_compartment = cfg.get("tenancy")
        except Exception:
            pass
    if not scope_compartment:
        raise ValueError("compartment_id is required (no default tenancy found)")

    counts: dict[str, int] = {}
    page: str | None = None
    while True:
        kwargs: dict[str, Any] = {
            "search_details": details,
            "compartment_id": scope_compartment,
            "compartment_id_in_subtree": include_subtree,
            "limit": 1000,
        }
        if page:
            kwargs["page"] = page
        resp = rs_client.search_resources(**kwargs)
        items = (
            getattr(resp.data, "items", [])
            if hasattr(resp, "data")
            else getattr(resp, "items", [])
        )
        for it in items or []:
            # ResourceSummary fields vary; handle dict/object
            rtype = (
                getattr(it, "resource_type", None)
                or getattr(it, "resourceType", None)
                or (it.get("resourceType") if isinstance(it, dict) else None)
            )
            key = str(rtype or "unknown")
            counts[key] = counts.get(key, 0) + 1
        page = getattr(resp, "opc_next_page", None)
        if not page:
            break

    return {
        "cost_by_service": cost.get("items", []),
        "resource_counts": counts,
        "scope": {
            "compartment_id": scope_compartment,
            "include_subtree": include_subtree,
        },
    }
