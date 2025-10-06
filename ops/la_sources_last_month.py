#!/usr/bin/env python3
import os
import sys
from typing import List, Dict

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

    # Build query for last 30 days using QueryDetails.time_filter (TimeRange)
    from datetime import datetime, timedelta, timezone
    query = "* | stats count as logrecords by 'Log Source' | sort -logrecords"

    from oci.log_analytics.models import QueryDetails, TimeRange
    time_start = datetime.now(timezone.utc) - timedelta(days=30)
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
    rows = []
    for row in (getattr(data, "rows", []) or []):
        vals = getattr(row, "values", None) or getattr(row, "data", None) or []
        if cols and len(cols) == len(vals):
            rows.append(dict(zip(cols, vals)))
        else:
            rows.append({"values": vals})

    # Try to map expected keys
    # Commonly, columns come back as ['Log Source', 'logrecords'] or similar; fallback to first two columns.
    src_key = None
    cnt_key = None
    for c in cols:
        if c.lower().replace(" ", "") in ["logsource", "source", "log_source"]:
            src_key = c
        if c.lower() in ["logrecords", "count"] or c.lower().replace(" ", "") in ["logrecords"]:
            cnt_key = c
    if not src_key and cols:
        src_key = cols[0]
    if not cnt_key and len(cols) > 1:
        cnt_key = cols[1]

    print(f"Logging Analytics Namespace: {ns}")
    print(f"Compartment: {comp}")
    print("")
    print("| Log Source | Events (30d) |")
    print("|------------|--------------:|")
    if src_key and cnt_key:
        for r in rows:
            src = r.get(src_key, "-")
            cnt = r.get(cnt_key, 0)
            print(f"| {src} | {cnt} |")
    else:
        # Fallback to printing raw rows
        for r in rows:
            print(f"| {r} |")


if __name__ == "__main__":
    run()
