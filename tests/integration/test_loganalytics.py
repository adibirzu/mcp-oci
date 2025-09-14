import datetime as dt
import os
import pytest

from mcp_oci_loganalytics.server import run_query


@pytest.mark.skipif(
    not os.environ.get("TEST_LOGANALYTICS_NAMESPACE"),
    reason="Set TEST_LOGANALYTICS_NAMESPACE to enable Log Analytics integration test",
)
def test_loganalytics_run_query(oci_profile, oci_region):
    namespace = os.environ["TEST_LOGANALYTICS_NAMESPACE"]
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

