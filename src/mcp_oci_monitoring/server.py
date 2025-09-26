"""MCP Server: OCI Monitoring
"""

from datetime import UTC
from typing import Any

from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.monitoring.MonitoringClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci_monitoring_list_metrics",
            "description": "List metric definitions in a compartment; optionally filter by namespace/name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "namespace": {"type": "string"},
                    "name": {"type": "string"},
                    "resource_group": {"type": "string"},
                    "compartment_id_in_subtree": {"type": "boolean", "default": False},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_metrics,
        },
        {
            "name": "oci_monitoring_summarize_metrics",
            "description": "Summarize metric data for a query between two times (UTC).",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "namespace": {"type": "string"},
                    "query": {"type": "string", "description": "e.g., CpuUtilization[1m].mean()"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "resolution": {"type": "string", "description": "e.g., 1m"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "namespace", "query", "start_time", "end_time"],
            },
            "handler": summarize_metrics,
        },
        {
            "name": "oci_monitoring_list_alarms",
            "description": "List alarms in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "lifecycle_state": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_alarms,
        },
        {
            "name": "oci_monitoring_get_alarm",
            "description": "Get an alarm by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alarm_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["alarm_id"],
            },
            "handler": get_alarm,
        },
        {
            "name": "oci_monitoring_list_metric_namespaces",
            "description": "Discover metric namespaces (derived from metric definitions).",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "compartment_id_in_subtree": {"type": "boolean", "default": False},
                    "limit_pages": {"type": "integer", "minimum": 1, "description": "Max pages to scan"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_metric_namespaces,
        },
        {
            "name": "oci_monitoring_list_resource_groups",
            "description": "Discover metric resource groups (derived from metric definitions).",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "namespace": {"type": "string", "description": "Optional filter to a namespace"},
                    "compartment_id_in_subtree": {"type": "boolean", "default": False},
                    "limit_pages": {"type": "integer", "minimum": 1},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_resource_groups,
        },
        {
            "name": "oci_monitoring_list_alarm_statuses",
            "description": "List alarm statuses in a compartment (if supported by SDK).",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_alarm_statuses,
        },
        {
            "name": "oci_monitoring_get_alarm_history",
            "description": "Get alarm history for a time range (evaluations/state changes).",
            "parameters": {
                "type": "object",
                "properties": {
                    "alarm_id": {"type": "string"},
                    "alarm_historytype": {"type": "string", "enum": ["STATE_TRANSITION_HISTORY", "STATELESS_PERIOD"]},
                    "timestamp_greater_than_or_equal_to": {"type": "string"},
                    "timestamp_less_than": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["alarm_id"],
            },
            "handler": get_alarm_history,
        },
        {
            "name": "oci_monitoring_summarize_metrics_window",
            "description": "Wrapper: summarize metrics for a recent window like 1h/24h with normalized resolution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "namespace": {"type": "string"},
                    "query": {"type": "string"},
                    "window": {"type": "string", "description": "e.g., 15m, 1h, 24h"},
                    "resolution": {"type": "string", "description": "Override auto resolution (e.g., 1m, 5m)"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "namespace", "query", "window"],
            },
            "handler": summarize_metrics_window,
        },
        {
            "name": "oci_monitoring_list_sdk_methods",
            "description": "Introspect available SDK methods on Monitoring and Alarm clients (for newer SDK versions).",
            "parameters": {"type": "object", "properties": {"profile": {"type": "string"}, "region": {"type": "string"}}},
            "handler": list_sdk_methods,
        },
        {
            "name": "oci_monitoring_common_compute_queries",
            "description": "Return common Compute metrics queries with suggested namespaces and help text.",
            "parameters": {"type": "object", "properties": {}},
            "handler": common_compute_queries,
        },
    ]


def list_metrics(compartment_id: str, namespace: str | None = None, name: str | None = None,
                 resource_group: str | None = None, compartment_id_in_subtree: bool = False,
                 limit: int | None = None, page: str | None = None,
                 profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {"compartment_id": compartment_id}
    if namespace:
        kwargs["namespace"] = namespace
    if name:
        kwargs["name"] = name
    if resource_group:
        kwargs["resource_group"] = resource_group
    if compartment_id_in_subtree:
        kwargs["compartment_id_in_subtree"] = compartment_id_in_subtree
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_metrics(**kwargs)
    items = [m.__dict__ for m in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def summarize_metrics(compartment_id: str, namespace: str, query: str,
                      start_time: str, end_time: str, resolution: str | None = None,
                      profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    client = create_client(profile=profile, region=region)
    models = oci.monitoring.models

    # Build SummarizeMetricsDataDetails robustly across SDK variants
    last_err: Exception | None = None
    details = None

    # Try legacy-friendly style: namespace and query on details (accepted by many SDK versions)
    for d_kwargs in (
        {"namespace": namespace, "query": query, "start_time": start_time, "end_time": end_time, "resolution": resolution},
        {"namespace": namespace, "query": query, "start_time": start_time, "end_time": end_time},
    ):
        try:
            details = models.SummarizeMetricsDataDetails(**{k: v for k, v in d_kwargs.items() if v})
            break
        except Exception as e:
            last_err = e

    # Fallback to official style: queries list + resolution at top level
    if details is None:
        try:
            mdq = models.MetricDataQuery(query=query)
            details = models.SummarizeMetricsDataDetails(
                start_time=start_time,
                end_time=end_time,
                queries=[mdq],
                resolution=resolution
            )
        except Exception as e:
            last_err = e

    if details is None:
        raise last_err or RuntimeError("Unable to build SummarizeMetricsDataDetails")

    # Call API with compartment_id parameter and details in body
    try:
        resp = client.summarize_metrics_data(
            compartment_id=compartment_id,
            summarize_metrics_data_details=details
        )
    except TypeError:
        # Fallback for older SDK signature: summarize_metrics_data(namespace, details, ...)
        resp = client.summarize_metrics_data(namespace, details)
    items = [d.__dict__ for d in getattr(resp, "data", [])]
    return with_meta(resp, {"items": items})


def _alarms_client(profile: str | None, region: str | None):
    # Try both names for safety
    cls = getattr(oci.monitoring, "AlarmClient", None) or getattr(oci.monitoring, "AlarmsClient", None)
    if cls is None:
        raise RuntimeError("Alarm client not available in SDK version")
    return make_client(cls, profile=profile, region=region)


def list_alarms(compartment_id: str, lifecycle_state: str | None = None, limit: int | None = None,
                page: str | None = None, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = _alarms_client(profile, region)
    kwargs: dict[str, Any] = {"compartment_id": compartment_id}
    if lifecycle_state:
        kwargs["lifecycle_state"] = lifecycle_state
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_alarms(**kwargs)
    items = [a.__dict__ for a in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_alarm(alarm_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = _alarms_client(profile, region)
    resp = client.get_alarm(alarm_id)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})


def list_metric_namespaces(compartment_id: str, compartment_id_in_subtree: bool = False,
                           limit_pages: int | None = None,
                           profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    # Prefer direct API if available in newer SDKs
    direct_candidates = ["list_namespaces", "list_metric_namespaces", "list_metrics_namespaces"]
    for name in direct_candidates:
        method = getattr(client, name, None)
        if method is None:
            continue
        try:
            kwargs: dict[str, Any] = {"compartment_id": compartment_id}
            if compartment_id_in_subtree:
                kwargs["compartment_id_in_subtree"] = True
            resp = method(**kwargs)
            # Assume response items carry a "namespace" or are strings
            data = getattr(resp, "data", [])
            if data and isinstance(data[0], str):
                return {"namespaces": sorted(set(data))}
            namespaces = sorted({getattr(x, "namespace", None) for x in data if getattr(x, "namespace", None)})
            return {"namespaces": namespaces}
        except Exception:
            continue
    # Fallback: derive from metric definitions
    seen = set()
    page = None
    pages = 0
    while True:
        kwargs: dict[str, Any] = {"compartment_id": compartment_id}
        if compartment_id_in_subtree:
            kwargs["compartment_id_in_subtree"] = True
        if page:
            kwargs["page"] = page
        resp = client.list_metrics(**kwargs)
        for md in getattr(resp, "data", []) or []:
            ns = getattr(md, "namespace", None)
            if ns:
                seen.add(ns)
        page = getattr(resp, "opc_next_page", None)
        pages += 1
        if not page or (limit_pages and pages >= limit_pages):
            break
    return {"namespaces": sorted(seen)}


def list_resource_groups(compartment_id: str, namespace: str | None = None, compartment_id_in_subtree: bool = False,
                         limit_pages: int | None = None,
                         profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    seen = set()
    page = None
    pages = 0
    while True:
        kwargs: dict[str, Any] = {"compartment_id": compartment_id}
        if namespace:
            kwargs["namespace"] = namespace
        if compartment_id_in_subtree:
            kwargs["compartment_id_in_subtree"] = True
        if page:
            kwargs["page"] = page
        resp = client.list_metrics(**kwargs)
        for md in getattr(resp, "data", []) or []:
            rg = getattr(md, "resource_group", None)
            if rg:
                seen.add(rg)
        page = getattr(resp, "opc_next_page", None)
        pages += 1
        if not page or (limit_pages and pages >= limit_pages):
            break
    return {"resource_groups": sorted(seen)}


def list_alarm_statuses(compartment_id: str, limit: int | None = None, page: str | None = None,
                        profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = _alarms_client(profile, region)
    method = getattr(client, "list_alarm_statuses", None)
    if method is None:
        raise RuntimeError("list_alarm_statuses not available in SDK version")
    kwargs: dict[str, Any] = {"compartment_id": compartment_id}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = method(**kwargs)
    items = [s.__dict__ for s in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_alarm_history(alarm_id: str, alarm_historytype: str | None = None,
                      timestamp_greater_than_or_equal_to: str | None = None,
                      timestamp_less_than: str | None = None,
                      profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = _alarms_client(profile, region)
    kwargs: dict[str, Any] = {"alarm_id": alarm_id}
    if alarm_historytype:
        kwargs["alarm_historytype"] = alarm_historytype
    if timestamp_greater_than_or_equal_to:
        kwargs["timestamp_greater_than_or_equal_to"] = timestamp_greater_than_or_equal_to
    if timestamp_less_than:
        kwargs["timestamp_less_than"] = timestamp_less_than
    method = getattr(client, "get_alarm_history", None)
    if method is None:
        raise RuntimeError("get_alarm_history not available in SDK version")
    resp = method(**kwargs)
    items = [h.__dict__ for h in getattr(resp, "data", [])]
    return with_meta(resp, {"items": items})


def _parse_window(window: str) -> int:
    # returns minutes
    units = {"m": 1, "h": 60, "d": 1440}
    window = window.strip().lower()
    for suffix, mult in units.items():
        if window.endswith(suffix):
            num = int(window[:-1])
            return num * mult
    # fallback assume minutes
    return int(window)


def _auto_resolution(minutes: int) -> str:
    if minutes <= 1440:  # <= 1 day
        return "1m"
    if minutes <= 7 * 1440:  # <= 7 days
        return "5m"
    return "1h"


def summarize_metrics_window(compartment_id: str, namespace: str, query: str, window: str,
                             resolution: str | None = None,
                             profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    from datetime import datetime, timedelta
    minutes = _parse_window(window)
    end_dt = datetime.now(UTC)
    # Round end to minute
    end_dt = end_dt.replace(second=0, microsecond=0)
    start_dt = end_dt - timedelta(minutes=minutes)
    res = resolution or _auto_resolution(minutes)
    return summarize_metrics(
        compartment_id=compartment_id,
        namespace=namespace,
        query=query,
        start_time=start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
        end_time=end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
        resolution=res,
        profile=profile,
        region=region,
    )


def list_sdk_methods(profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    alarms = None
    try:
        alarms = _alarms_client(profile, region)
    except Exception:
        pass
    def _methods(obj):
        out = []
        for name in dir(obj):
            if name.startswith("_"):
                continue
            ref = getattr(obj, name)
            if callable(ref):
                out.append(name)
        return sorted(out)
    return {
        "monitoring_methods": _methods(client),
        "alarm_methods": _methods(alarms) if alarms else [],
    }


def common_compute_queries() -> dict[str, Any]:
    return {
        "namespace": "oci_computeagent",
        "queries": [
            {
                "name": "CPU mean (1m)",
                "query": "CpuUtilization[1m].mean()",
                "description": "Average CPU utilization at 1-minute resolution",
            },
            {
                "name": "CPU max (5m)",
                "query": "CpuUtilization[5m].max()",
                "description": "Max CPU utilization at 5-minute resolution",
            },
            {
                "name": "Memory mean (1m)",
                "query": "MemoryUtilization[1m].mean()",
                "description": "Average memory utilization at 1-minute resolution (requires compute agent metrics)",
            },
            {
                "name": "Disk usage (5m)",
                "query": "FilesystemUsage[5m].mean()",
                "description": "Average filesystem usage at 5-minute resolution",
            },
        ],
        "usage": "Use summarize-metrics or summarize-metrics-window with the query string",
    }
