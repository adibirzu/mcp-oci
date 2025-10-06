import datetime as dt

import pytest

from mcp_oci_loganalytics.server import run_query


def test_loganalytics_run_query(oci_profile, oci_region, log_analytics_namespace):
    if not log_analytics_namespace:
        pytest.skip("No Log Analytics namespace discovered; set TEST_LOGANALYTICS_NAMESPACE to force")
    namespace = log_analytics_namespace
    # 1-hour window ending now
    end = dt.datetime.utcnow().replace(microsecond=0)
    start = end - dt.timedelta(hours=1)
    out = run_query(
        namespace_name=namespace,
        query_string='stats count() by "__logSource__" | sort -count | limit 5',
        time_start=start.isoformat() + "Z",
        time_end=end.isoformat() + "Z",
        max_total_count=10,
        profile=oci_profile,
        region=oci_region,
    )
    assert isinstance(out, dict)
    assert any(k in out for k in ("items", "result"))
