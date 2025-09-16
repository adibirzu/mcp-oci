import datetime as dt
from typing import Any

import pytest

from mcp_oci_usageapi.server import request_summarized_usages


@pytest.mark.parametrize("days", [7])
def test_usageapi_summarized_costs(oci_profile, oci_region, tenancy_ocid, days):
    # last `days` days, rounded to midnight UTC per Usage API requirements
    today = dt.datetime.now(dt.UTC).date()
    end_dt = dt.datetime.combine(today, dt.time(0, 0, 0, tzinfo=dt.UTC))
    start_dt = end_dt - dt.timedelta(days=days)
    end_iso = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    start_iso = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    out: dict[str, Any] = request_summarized_usages(
        tenant_id=tenancy_ocid,
        time_usage_started=start_iso,
        time_usage_ended=end_iso,
        granularity="DAILY",
        query_type="COST",
        group_by=["service"],
        profile=oci_profile,
        region=oci_region,
    )
    assert "items" in out
