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
            "name": "oci:usageapi:request-summarized-usages",
            "description": "Request summarized usage or cost between two timestamps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_id": {"type": "string"},
                    "time_usage_started": {"type": "string", "description": "ISO8601"},
                    "time_usage_ended": {"type": "string", "description": "ISO8601"},
                    "granularity": {"type": "string", "enum": ["DAILY", "MONTHLY"], "default": "DAILY"},
                    "query_type": {"type": "string", "enum": ["USAGE", "COST"], "default": "COST"},
                    "group_by": {"type": "array", "items": {"type": "string"}},
                    "dimensions": {"type": "object", "additionalProperties": {"type": "string"}, "description": "Optional server-side dimensions filter (e.g., {\"service\": \"Compute\"})"},
                    "tags": {"type": "object", "additionalProperties": {"type": "string"}, "description": "Optional server-side tags filter"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenant_id", "time_usage_started", "time_usage_ended"],
            },
            "handler": request_summarized_usages,
        },
        {
            "name": "oci:usageapi:cost-by-service",
            "description": "Convenience: Summarized COST grouped by service for the last N days (times normalized to midnight UTC). Optional client-side service filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_id": {"type": "string"},
                    "days": {"type": "integer", "minimum": 1, "default": 7},
                    "granularity": {"type": "string", "enum": ["DAILY", "MONTHLY"], "default": "DAILY"},
                    "service_name": {"type": "string", "description": "Optional client-side filter"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenant_id"],
            },
            "handler": cost_by_service,
        },
        {
            "name": "oci:usageapi:cost-by-compartment",
            "description": "Convenience: Summarized COST grouped by compartmentId for last N days (midnight UTC). Optional client-side compartment filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_id": {"type": "string"},
                    "days": {"type": "integer", "minimum": 1, "default": 7},
                    "granularity": {"type": "string", "enum": ["DAILY", "MONTHLY"], "default": "DAILY"},
                    "compartment_id": {"type": "string", "description": "Optional client-side filter"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenant_id"],
            },
            "handler": cost_by_compartment,
        },
        {
            "name": "oci:usageapi:usage-by-service",
            "description": "Convenience: Summarized USAGE grouped by service for last N days (midnight UTC). Optional service filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_id": {"type": "string"},
                    "days": {"type": "integer", "minimum": 1, "default": 7},
                    "granularity": {"type": "string", "enum": ["DAILY", "MONTHLY"], "default": "DAILY"},
                    "service_name": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenant_id"],
            },
            "handler": usage_by_service,
        },
        {
            "name": "oci:usageapi:usage-by-compartment",
            "description": "Convenience: Summarized USAGE grouped by compartmentId for last N days (midnight UTC). Optional compartment filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_id": {"type": "string"},
                    "days": {"type": "integer", "minimum": 1, "default": 7},
                    "granularity": {"type": "string", "enum": ["DAILY", "MONTHLY"], "default": "DAILY"},
                    "compartment_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenant_id"],
            },
            "handler": usage_by_compartment,
        },
        {
            "name": "oci:usageapi:showusage-run",
            "description": "Run Oracle showusage example tool and return its output (requires local clone).",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "ISO8601 start"},
                    "end": {"type": "string", "description": "ISO8601 end"},
                    "granularity": {"type": "string", "enum": ["DAILY", "MONTHLY"], "default": "DAILY"},
                    "groupby": {"type": "string", "description": "e.g., service"},
                    "extra_args": {"type": "string", "description": "additional CLI flags"},
                    "expect_json": {"type": "boolean", "default": False},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                    "path": {"type": "string", "description": "Path to showusage.py (optional)"},
                },
                "required": ["start", "end"],
            },
            "handler": showusage_run,
        },
        {
            "name": "oci:usageapi:list-rate-cards",
            "description": "List rate cards (list price) for a subscription.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subscription_id": {"type": "string"},
                    "time_from": {"type": "string", "description": "ISO8601; optional"},
                    "time_to": {"type": "string", "description": "ISO8601; optional"},
                    "part_number": {"type": "string", "description": "Optional product part number to filter client-side"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["subscription_id"],
            },
            "handler": list_rate_cards,
        },
    ]


def request_summarized_usages(tenant_id: str, time_usage_started: str, time_usage_ended: str,
                               granularity: str = "DAILY", query_type: str = "COST",
                               group_by: list[str] | None = None,
                               dimensions: dict[str, str] | None = None,
                               tags: dict[str, str] | None = None,
                               profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    client = create_client(profile=profile, region=region)
    # Normalize times to meet API precision requirements for DAILY/MONTHLY
    t_start = _normalize_utc_midnight(time_usage_started) if granularity in ("DAILY", "MONTHLY") else time_usage_started
    t_end = _normalize_utc_midnight(time_usage_ended) if granularity in ("DAILY", "MONTHLY") else time_usage_ended
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


def cost_by_service(tenant_id: str, days: int = 7, granularity: str = "DAILY",
                    service_name: str | None = None,
                    profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    from datetime import datetime, timedelta
    today = datetime.now(UTC).date()
    end_dt = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    start_dt = end_dt - timedelta(days=days)
    result = request_summarized_usages(
        tenant_id=tenant_id,
        time_usage_started=start_dt.strftime('%Y-%m-%dT00:00:00Z'),
        time_usage_ended=end_dt.strftime('%Y-%m-%dT00:00:00Z'),
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


def cost_by_compartment(tenant_id: str, days: int = 7, granularity: str = "DAILY",
                        compartment_id: str | None = None,
                        profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    from datetime import datetime, timedelta
    today = datetime.now(UTC).date()
    end_dt = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    start_dt = end_dt - timedelta(days=days)
    result = request_summarized_usages(
        tenant_id=tenant_id,
        time_usage_started=start_dt.strftime('%Y-%m-%dT00:00:00Z'),
        time_usage_ended=end_dt.strftime('%Y-%m-%dT00:00:00Z'),
        granularity=granularity,
        query_type="COST",
        group_by=["compartmentId"],
        profile=profile,
        region=region,
    )
    if compartment_id and isinstance(result.get("items"), list):
        items = [i for i in result["items"] if str(i.get("compartmentId")) == compartment_id]
        result["items"] = items
    return result


def usage_by_service(tenant_id: str, days: int = 7, granularity: str = "DAILY",
                     service_name: str | None = None,
                     profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    from datetime import datetime, timedelta
    today = datetime.now(UTC).date()
    end_dt = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    start_dt = end_dt - timedelta(days=days)
    result = request_summarized_usages(
        tenant_id=tenant_id,
        time_usage_started=start_dt.strftime('%Y-%m-%dT00:00:00Z'),
        time_usage_ended=end_dt.strftime('%Y-%m-%dT00:00:00Z'),
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


def usage_by_compartment(tenant_id: str, days: int = 7, granularity: str = "DAILY",
                         compartment_id: str | None = None,
                         profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    from datetime import datetime, timedelta
    today = datetime.now(UTC).date()
    end_dt = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    start_dt = end_dt - timedelta(days=days)
    result = request_summarized_usages(
        tenant_id=tenant_id,
        time_usage_started=start_dt.strftime('%Y-%m-%dT00:00:00Z'),
        time_usage_ended=end_dt.strftime('%Y-%m-%dT00:00:00Z'),
        granularity=granularity,
        query_type="USAGE",
        group_by=["compartmentId"],
        profile=profile,
        region=region,
    )
    if compartment_id and isinstance(result.get("items"), list):
        items = [i for i in result["items"] if str(i.get("compartmentId")) == compartment_id]
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


def list_rate_cards(subscription_id: str, time_from: str | None = None, time_to: str | None = None,
                    part_number: str | None = None,
                    profile: str | None = None, region: str | None = None) -> dict[str, Any]:
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


def showusage_run(start: str, end: str, granularity: str = "DAILY", groupby: str | None = None,
                  extra_args: str | None = None, expect_json: bool = False,
                  profile: str | None = None, region: str | None = None, path: str | None = None) -> dict[str, Any]:
    import os
    import subprocess

    from mcp_oci_common.parsing import parse_json_loose, parse_kv_lines
    script = path or os.environ.get("SHOWUSAGE_PATH") or "third_party/oci-python-sdk/examples/showusage/showusage.py"
    if not os.path.exists(script):
        raise RuntimeError("showusage.py not found; set SHOWUSAGE_PATH or place under third_party/.../showusage.py")
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
