from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_monitoring(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-monitoring-fast") -> None:
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )
    from mcp_oci_monitoring.server import (
        list_metrics,
        summarize_metrics,
        list_alarms,
        get_alarm,
        list_alarm_statuses,
        get_alarm_history,
        list_metric_namespaces,
        list_resource_groups,
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
    async def oci_monitoring_list_metrics(compartment_id: str, namespace: str = None, name: str = None,
                                          limit: int = None, page: str = None,
                                          profile: str = None, region: str = None):
        args = {
            "compartment_id": compartment_id,
            "namespace": namespace,
            "name": name,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_metrics(**args)

    @app.tool()
    async def oci_monitoring_summarize_metrics(compartment_id: str, namespace: str, query: str,
                                               start_time: str, end_time: str, resolution: str = None,
                                               limit: int = None, page: str = None,
                                               profile: str = None, region: str = None):
        args = {
            "compartment_id": compartment_id,
            "namespace": namespace,
            "query": query,
            "start_time": start_time,
            "end_time": end_time,
            "resolution": resolution,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return summarize_metrics(**args)

    @app.tool()
    async def oci_monitoring_list_alarms(compartment_id: str, lifecycle_state: str = None,
                                         limit: int = None, page: str = None,
                                         profile: str = None, region: str = None):
        args = {
            "compartment_id": compartment_id,
            "lifecycle_state": lifecycle_state,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_alarms(**args)

    @app.tool()
    async def oci_monitoring_get_alarm(alarm_id: str, profile: str = None, region: str = None):
        args = {
            "alarm_id": alarm_id,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return get_alarm(**args)

    @app.tool()
    async def oci_monitoring_get_alarm_history(alarm_id: str, alarm_historytype: str = None,
                                               limit: int = None, page: str = None,
                                               profile: str = None, region: str = None):
        args = {
            "alarm_id": alarm_id,
            "alarm_historytype": alarm_historytype,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return get_alarm_history(**args)

    @app.tool()
    async def oci_monitoring_list_metric_namespaces(compartment_id: str, compartment_id_in_subtree: bool = False,
                                                    limit: int = None, page: str = None,
                                                    profile: str = None, region: str = None):
        args = {
            "compartment_id": compartment_id,
            "compartment_id_in_subtree": compartment_id_in_subtree,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_metric_namespaces(**args)

    @app.tool()
    async def oci_monitoring_list_resource_groups(compartment_id: str, namespace: str = None,
                                                  compartment_id_in_subtree: bool = False,
                                                  limit: int = None, page: str = None,
                                                  profile: str = None, region: str = None):
        args = {
            "compartment_id": compartment_id,
            "namespace": namespace,
            "compartment_id_in_subtree": compartment_id_in_subtree,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_resource_groups(**args)

    @app.tool()
    async def oci_monitoring_list_alarm_statuses(compartment_id: str, limit: int = None, page: str = None,
                                                 profile: str = None, region: str = None):
        args = {
            "compartment_id": compartment_id,
            "limit": limit,
            "page": page,
            "profile": profile,
            "region": region,
        }
        args = _with_defaults(args)
        return list_alarm_statuses(**args)

    @app.tool()
    async def get_server_info():
        return {"name": server_name, "framework": "fastmcp", "service": "monitoring", "defaults": {"profile": profile, "region": region}}

    app.run()
