#!/usr/bin/env python3
import os
import sys

# Ensure repo paths
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import oci  # type: ignore
from mcp_oci_common.config import get_oci_config, get_compartment_id  # type: ignore


def resolve_namespace(la_client, tenancy_id: str) -> str:
    resp = la_client.list_namespaces(compartment_id=tenancy_id)
    items = getattr(getattr(resp, "data", None), "items", []) or []
    names = [getattr(n, "namespace_name", None) or getattr(n, "name", None) for n in items]
    names = [n for n in names if n]
    if not names:
        raise RuntimeError("No Logging Analytics namespaces found. Is LA enabled?")
    if len(names) > 1:
        ns_env = os.getenv("LA_NAMESPACE")
        if ns_env and ns_env in names:
            return ns_env
        raise RuntimeError(f"Multiple namespaces found: {names}. Set LA_NAMESPACE to one of them and retry.")
    return names[0]


def run():
    cfg = get_oci_config()
    tenancy = cfg.get("tenancy") or os.getenv("COMPARTMENT_OCID")
    if not tenancy:
        raise RuntimeError("Unable to resolve tenancy OCID from config or COMPARTMENT_OCID")

    comp = get_compartment_id() or tenancy
    la = oci.log_analytics.LogAnalyticsClient(cfg)
    ns = os.getenv("LA_NAMESPACE") or resolve_namespace(la, tenancy)

    # Last 60 minutes table of sources
    from datetime import datetime, timedelta, timezone
    query = "* | stats count as logrecords by 'Log Source' | sort -logrecords"

    from oci.log_analytics.models import QueryDetails, TimeRange
    time_start = datetime.now(timezone.utc) - timedelta(minutes=60)
    time_end = datetime.now(timezone.utc)
    time_filter = TimeRange(time_start=time_start, time_end=time_end, time_zone="Europe/Bucharest")

    qd = QueryDetails(
        query_string=query,
        compartment_id=comp,
        compartment_id_in_subtree=True,
        sub_system="LOG",
        max_total_count=2000,
        should_include_total_count=True,
        time_filter=time_filter
    )

    resp = la.query(namespace_name=ns, query_details=qd, limit=2000)
    data = resp.data
    cols = [getattr(c, "column_name", None) or getattr(c, "name", None) or f"col_{i}" for i, c in enumerate(getattr(data, "columns", []) or [])]

    # Determine likely column keys
    src_key = None
    cnt_key = None
    for c in cols:
        cl = c.lower().replace(" ", "")
        if cl in ["logsource", "source", "log_source"]:
            src_key = c
        if cl in ["logrecords", "count"]:
            cnt_key = c
    if not src_key and cols:
        src_key = cols[0]
    if not cnt_key and len(cols) > 1:
        cnt_key = cols[1]

    print(f"Logging Analytics Namespace: {ns}")
    print(f"Compartment (incl. subtree): {comp}")
    print("")
    print("| Log Source | Events (last 60m) |")
    print("|------------|-------------------:|")

    rows = getattr(data, "rows", []) or []
    if not rows:
        return

    for row in rows:
        vals = getattr(row, "values", None) or getattr(row, "data", None) or []
        if cols and len(cols) == len(vals):
            if src_key and cnt_key:
                src = vals[cols.index(src_key)]
                cnt = vals[cols.index(cnt_key)]
                print(f"| {src} | {cnt} |")
            else:
                print(f"| {vals} |")
        else:
            print(f"| {vals} |")


if __name__ == "__main__":
    run()
