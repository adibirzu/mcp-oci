#!/usr/bin/env python3
import os
import sys
from typing import List, Dict, Optional

# Ensure repo paths
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import oci  # type: ignore
from mcp_oci_common.config import get_oci_config, get_compartment_id  # type: ignore


def resolve_namespace(la_client, cfg) -> str:
    """
    Prefer get_namespace(); fallback to list_namespaces on tenancy OCID.
    """
    try:
        ns = la_client.get_namespace().data
        if isinstance(ns, str) and ns:
            return ns
    except Exception:
        pass
    tenancy_id = cfg.get("tenancy") or os.getenv("COMPARTMENT_OCID")
    if not tenancy_id:
        raise RuntimeError("Unable to resolve tenancy OCID for namespace lookup")
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
    # Honour explicit region override if provided
    cfg = cfg.copy()
    cfg["region"] = os.getenv("LOGAN_REGION", cfg.get("region") or "eu-frankfurt-1")

    comp = get_compartment_id() or (cfg.get("tenancy") or os.getenv("COMPARTMENT_OCID"))
    if not comp:
        raise RuntimeError("Unable to resolve compartment/tenancy OCID")

    la = oci.log_analytics.LogAnalyticsClient(cfg)
    ns = os.getenv("LA_NAMESPACE") or resolve_namespace(la, cfg)

    from datetime import datetime, timezone, timedelta
    from oci.log_analytics.models import QueryDetails, TimeRange

    now = datetime.now(timezone.utc)
    tz = os.getenv("TIME_ZONE", "UTC")
    time_filter = TimeRange(time_start=now - timedelta(hours=24), time_end=now, time_zone=tz)

    # Use the variant that works per tenancy (simple 'count as ...')
    qd = QueryDetails(
        query_string="* | stats count as logrecords by 'Log Source' | sort -logrecords",
        compartment_id=comp,
        compartment_id_in_subtree=True,
        sub_system="LOG",
        max_total_count=5000,
        should_include_total_count=True,
        should_run_async=False,
        time_filter=time_filter,
    )

    resp = la.query(namespace_name=ns, query_details=qd, limit=5000)
    data = getattr(resp, "data", None)

    # Gather columns
    cols = [getattr(c, "column_name", None) or getattr(c, "name", None) or f"col_{i}" for i, c in enumerate(getattr(data, "columns", []) or [])]

    print(f"Logging Analytics Namespace: {ns}")
    print(f"Compartment (incl. subtree): {comp}")
    print("")
    print("| Log Source | Events (last 24h) |")
    print("|------------|-------------------:|")

    # Prefer dict-style items if present
    items = getattr(data, "items", []) or []
    if items and isinstance(items, list) and isinstance(items[0], dict):
        # Heuristically find source and count keys
        src_key: Optional[str] = None
        cnt_key: Optional[str] = None
        # Try from column names first
        for c in cols:
            cl = (c or "").lower().replace(" ", "")
            if cl in ("logsource", "source", "log_source"):
                src_key = c
            if cl in ("logrecords", "count"):
                cnt_key = c
        # Fallback from dict keys
        if items and not (src_key and cnt_key):
            for k in items[0].keys():
                kl = str(k).lower()
                if not src_key and ("log source" in kl or "logsource" in kl or kl == "source"):
                    src_key = k
                if not cnt_key and (kl in ("logrecords", "count") or "records" in kl):
                    cnt_key = k
        printed = False
        for it in items:
            src = it.get(src_key, "-") if src_key else next(iter(it.values()), "-")
            cnt = it.get(cnt_key, 0) if cnt_key else (list(it.values())[1] if len(it.values()) > 1 else 0)
            print(f"| {src} | {cnt} |")
            printed = True
        if not printed:
            print("| (no sources found) | 0 |")
        return

    # Row/column style
    rows = getattr(data, "rows", []) or []
    if not rows:
        print("| (no sources found) | 0 |")
        return

    # Identify indices
    src_idx = None
    cnt_idx = None
    for i, c in enumerate(cols):
        cl = (c or "").lower().replace(" ", "")
        if src_idx is None and cl in ("logsource", "source", "log_source"):
            src_idx = i
        if cnt_idx is None and cl in ("logrecords", "count"):
            cnt_idx = i

    for row in rows:
        vals = getattr(row, "values", None) or getattr(row, "data", None) or []
        if cols and len(cols) == len(vals):
            src = vals[src_idx] if (src_idx is not None and src_idx < len(vals)) else (vals[0] if vals else "-")
            cnt = vals[cnt_idx] if (cnt_idx is not None and cnt_idx < len(vals)) else (vals[1] if len(vals) > 1 else 0)
            print(f"| {src} | {cnt} |")
        else:
            print(f"| {vals} |")


if __name__ == "__main__":
    run()
