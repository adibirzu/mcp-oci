#!/usr/bin/env python3
import os
import sys
from typing import Optional, List

# Ensure repo paths
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import oci  # type: ignore
from mcp_oci_common.config import get_oci_config, get_compartment_id  # type: ignore


def resolve_namespace(la_client) -> str:
    """
    Prefer get_namespace() when available; fallback to list_namespaces on tenancy.
    """
    try:
        ns = la_client.get_namespace().data
        if isinstance(ns, str) and ns:
            return ns
    except Exception:
        pass
    # Fallback to list_namespaces on tenancy
    cfg = get_oci_config()
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


def choose_query_variant(la_client, namespace: str, compartment_id: str, time_filter) -> Optional[oci.log_analytics.models.QueryDetails]:
    """
    Try multiple stats variants to handle parser differences across tenancies.
    Returns QueryDetails that yields rows, or last tried variant if none returned rows.
    """
    from oci.log_analytics.models import QueryDetails
    variants: List[str] = [
        "* | stats count as logrecords by 'Log Source' | sort -logrecords",
        "* | stats COUNT as logrecords by 'Log Source' | sort -logrecords",
        "* | stats COUNT() as logrecords by 'Log Source' | sort -logrecords",
    ]
    first_qd: Optional[QueryDetails] = None
    for q in variants:
        qd = QueryDetails(
            query_string=q,
            compartment_id=compartment_id,
            compartment_id_in_subtree=True,
            sub_system="LOG",
            max_total_count=5000,
            should_include_total_count=True,
            time_filter=time_filter
        )
        if first_qd is None:
            first_qd = qd
        try:
            resp = la_client.query(namespace_name=namespace, query_details=qd, limit=5000)
            data = getattr(resp, "data", None)
            rows = getattr(data, "rows", []) or []
            if rows:
                return qd
        except oci.exceptions.ServiceError:
            continue
    return first_qd


def run():
    # Config with optional region override (fallback to current region)
    cfg = get_oci_config()
    cfg = cfg.copy()
    cfg["region"] = os.getenv("LOGAN_REGION", cfg.get("region") or "eu-frankfurt-1")

    comp = get_compartment_id() or (cfg.get("tenancy") or os.getenv("COMPARTMENT_OCID"))
    if not comp:
        raise RuntimeError("Unable to resolve compartment/tenancy OCID")

    la = oci.log_analytics.LogAnalyticsClient(cfg)
    ns = os.getenv("LA_NAMESPACE") or resolve_namespace(la)

    from datetime import datetime, timedelta, timezone
    from oci.log_analytics.models import TimeRange

    now = datetime.now(timezone.utc)
    tz = os.getenv("TIME_ZONE", "UTC")
    time_filter = TimeRange(time_start=now - timedelta(hours=24), time_end=now, time_zone=tz)

    qd = choose_query_variant(la, ns, comp, time_filter)
    if qd is None:
        print("Logging Analytics Namespace:", ns)
        print("Compartment (incl. subtree):", comp)
        print("")
        print("| Log Source | Events (last 24h) |")
        print("|------------|-------------------:|")
        print("| (no sources found) | 0 |")
        return

    try:
        resp = la.query(namespace_name=ns, query_details=qd, limit=5000)
    except oci.exceptions.ServiceError:
        print(f"Logging Analytics Namespace: {ns}")
        print(f"Compartment (incl. subtree): {comp}")
        print("")
        print("| Log Source | Events (last 24h) |")
        print("|------------|-------------------:|")
        print("| (no sources found) | 0 |")
        return
    data = getattr(resp, "data", None)

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
    print("| Log Source | Events (last 24h) |")
    print("|------------|-------------------:|")

    rows = getattr(data, "rows", []) or []
    if not rows:
        print("| (no sources found) | 0 |")
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
