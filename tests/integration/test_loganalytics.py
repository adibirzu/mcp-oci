import datetime as dt

import pytest

from mcp_servers.loganalytics.server import execute_query


def test_loganalytics_run_query(oci_profile, oci_region, log_analytics_namespace):
    if not log_analytics_namespace:
        pytest.skip("No Log Analytics namespace discovered; set TEST_LOGANALYTICS_NAMESPACE to force")
    # 1-hour window ending now
    end = dt.datetime.utcnow().replace(microsecond=0)
    start = end - dt.timedelta(hours=1)
    out = execute_query(
        query='stats count() by "Log Source" | sort -count | limit 5',
        compartment_id=log_analytics_namespace,
        time_range="1h",
        max_count=10,
        profile=oci_profile,
        region=oci_region,
    )
    assert isinstance(out, dict)
    assert "results" in out
