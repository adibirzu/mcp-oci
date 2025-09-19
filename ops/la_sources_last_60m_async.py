#!/usr/bin/env python3
import os
import sys
import time

# Ensure repo paths
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import oci  # type: ignore
from mcp_oci_common.config import get_oci_config, get_compartment_id  # type: ignore


def resolve_namespace(la_client, tenancy_id: str) -> str:
    # Prefer get_namespace() when available (returns current/default namespace string)
    try:
        ns = la_client.get_namespace().data
        if isinstance(ns, str) and ns:
            return ns
    except Exception:
        pass

    # Fallback to list_namespaces
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

    from datetime import datetime, timedelta, timezone
    from oci.log_analytics.models import QueryDetails, TimeRange

    # Query for last 60 minutes, async, then poll using workRequestId
    query = "* | stats count as logrecords by 'Log Source' | sort -logrecords"
    now = datetime.now(timezone.utc)
    tr = TimeRange(time_start=now - timedelta(minutes=60), time_end=now, time_zone=os.getenv("TIME_ZONE", "UTC"))

    qd = QueryDetails(
        query_string=query,
        compartment_id=comp,
        compartment_id_in_subtree=True,
        sub_system="LOG",
        max_total_count=5000,
        should_include_total_count=True,
        should_run_async=True,
        time_filter=tr
    )

    # Submit async query
    submit = la.query(namespace_name=ns, query_details=qd, limit=5000)
    work_request_id = None
    # Try both header and payload for work request id
    work_request_id = submit.headers.get("opc-work-request-id") if hasattr(submit, "headers") else None
    if not work_request_id and hasattr(submit, "data"):
        work_request_id = getattr(submit.data, "work_request_id", None)

    if not work_request_id:
        raise RuntimeError("Failed to obtain work request id for async query")

    # Poll for results using GET query result with flags (Console mirrors this)
    # Honor Retry-After header if present
    print(f"Logging Analytics Namespace: {ns}")
    print(f"Compartment (incl. subtree): {comp}")
    print("")
    print("| Log Source | Events (last 60m) |")
    print("|------------|-------------------:|")

    # Poll loop
    attempts = 0
    while True:
        attempts += 1
        res = la.get_query_result(
            namespace_name=ns,
            work_request_id=work_request_id,
            should_include_columns=True,
            should_include_fields=True
        )
        data = getattr(res, "data", None)
        # Try to detect lifecycle end states if available on data
        lifecycle = getattr(data, "lifecycle_state", None)
        # Extract columns and possible result containers
        cols = [getattr(c, "column_name", None) or getattr(c, "name", None) or f"col_{i}" for i, c in enumerate(getattr(data, "columns", []) or [])]
        items = getattr(data, "items", []) or []
        rows = getattr(data, "rows", []) or []

        # Prefer 'items' (dict-based results, as used by Console GET)
        if items:
            # Determine likely keys
            src_key = None
            cnt_key = None
            # Try from columns if present
            for c in cols:
                cl = c.lower().replace(" ", "")
                if cl in ["logsource", "source", "log_source"]:
                    src_key = c
                if cl in ["logrecords", "count"]:
                    cnt_key = c
            # If columns not helpful, inspect dict keys
            if items and not (src_key and cnt_key):
                for k in items[0].keys():
                    kl = str(k).lower()
                    if not src_key and ("log source" in kl or "logsource" in kl or "source" == kl):
                        src_key = k
                    if not cnt_key and (kl in ["logrecords", "count"] or "records" in kl):
                        cnt_key = k
            for it in items:
                if isinstance(it, dict):
                    src = it.get(src_key, "-") if src_key else next(iter(it.values()), "-")
                    cnt = it.get(cnt_key, 0) if cnt_key else list(it.values())[1] if len(it.values()) > 1 else 0
                    print(f"| {src} | {cnt} |")
                else:
                    print(f"| {it} |")
            return

        if rows:
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

            for row in rows:
                vals = getattr(row, "values", None) or getattr(row, "data", None) or []
                if cols and len(cols) == len(vals) and src_key and cnt_key:
                    src = vals[cols.index(src_key)]
                    cnt = vals[cols.index(cnt_key)]
                    print(f"| {src} | {cnt} |")
                else:
                    print(f"| {vals} |")
            return

        # If lifecycle explicitly finished but no rows, stop
        if lifecycle in ("SUCCEEDED", "FAILED", "CANCELED"):
            # No results
            return

        # Retry-After header controls cadence
        sleep_s = 0.5
        try:
            sleep_hdr = res.headers.get("retry-after") if hasattr(res, "headers") else None
            if sleep_hdr:
                sleep_s = float(sleep_hdr)
        except Exception:
            pass

        time.sleep(max(0.2, sleep_s))
        if attempts > 120:  # ~1–2 minutes
            return


if __name__ == "__main__":
    run()
