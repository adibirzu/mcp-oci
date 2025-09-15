from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None


def run_usageapi(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-usageapi-fast") -> None:
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )
    from mcp_oci_usageapi.server import (
        request_summarized_usages,
        cost_by_service,
        cost_by_compartment,
        usage_by_service,
        usage_by_compartment,
        list_rate_cards,
        showusage_run,
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
    async def oci_usage_request_summarized_usages(
        tenant_id: str,
        time_usage_started: str,
        time_usage_ended: str,
        granularity: str = "DAILY",
        query_type: str = "COST",
        group_by: list = None,
        dimensions: dict = None,
        tags: dict = None,
        profile: str = None,
        region: str = None,
    ):
        return request_summarized_usages(**_with_defaults(locals()))

    @app.tool()
    async def oci_usage_cost_by_service(tenant_id: str, days: int = 7, granularity: str = "DAILY", service_name: str = None,
                                        profile: str = None, region: str = None):
        return cost_by_service(**_with_defaults(locals()))

    @app.tool()
    async def oci_usage_cost_by_compartment(tenant_id: str, days: int = 7, granularity: str = "DAILY", compartment_id: str = None,
                                            profile: str = None, region: str = None):
        return cost_by_compartment(**_with_defaults(locals()))

    @app.tool()
    async def oci_usage_usage_by_service(tenant_id: str, days: int = 7, granularity: str = "DAILY", service_name: str = None,
                                         profile: str = None, region: str = None):
        return usage_by_service(**_with_defaults(locals()))

    @app.tool()
    async def oci_usage_usage_by_compartment(tenant_id: str, days: int = 7, granularity: str = "DAILY", compartment_id: str = None,
                                             profile: str = None, region: str = None):
        return usage_by_compartment(**_with_defaults(locals()))

    @app.tool()
    async def oci_usage_list_rate_cards(subscription_id: str, time_from: str = None, time_to: str = None,
                                        part_number: str = None, profile: str = None, region: str = None):
        return list_rate_cards(**_with_defaults(locals()))

    @app.tool()
    async def oci_usage_showusage_run(start: str, end: str, granularity: str = "DAILY", groupby: str = None, extra_args: str = None,
                                      expect_json: bool = False, profile: str = None, region: str = None, path: str = None):
        return showusage_run(**_with_defaults(locals()))

    @app.tool()
    async def get_server_info():
        return {"name": server_name, "framework": "fastmcp", "service": "usageapi", "defaults": {"profile": profile, "region": region}}

    app.run()