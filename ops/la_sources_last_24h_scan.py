#!/usr/bin/env python3
import os
import sys
from typing import List, Dict, Tuple

# Ensure repo paths
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import oci  # type: ignore
from mcp_oci_common.config import get_oci_config  # type: ignore


def resolve_namespace(la_client, tenancy_id: str) -> str:
    # Prefer get_namespace() when available (returns namespace string)
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


def list_all_compartments(identity_client, tenancy_id: str) -> List[Tuple[str, str]]:
    """
    Returns list of (display_name, id) including tenancy root and all active subcompartments.
    """
    out: List[Tuple[str, str]] = [("tenancy-root", tenancy_id)]
    try:
        page = None
        while True:
            resp = identity_client.list_compartments(
                compartment_id=tenancy_id,
                compartment_id_in_subtree=True,
                access_level="ANY",
                page=page,
            )
            for comp in resp.data:
                if getattr(comp, "lifecycle_state", "") == "ACTIVE":
                    out.append((getattr(comp, "name", getattr(comp, "display_name", comp.id)), comp.id))
            page = resp.headers.get("opc-next-page")
            if not page:
                break
    except Exception:
        pass
    # de-dup ids preserving order
    seen = set()
    deduped: List[Tuple[str, str]] = []
    for name, cid in out:
        if cid not in seen:
            deduped.append((name, cid))
            seen.add(cid)
    return deduped


def query_sources_last_24h(la_client, namespace: str, compartment_id: str) -> List[Dict]:
    """
    Run a synchronous LA query for last 24h in one compartment and return normalized rows.
    """
    from datetime import datetime, timezone, timedelta
    from oci.log_analytics.models import QueryDetails, TimeRange

    now = datetime.now(timezone.utc)
    # Use UTC by default; allow override via TIME_ZONE
    time_filter = TimeRange(
        time_start=now - timedelta(hours=24),
        time_end=now,
        time_zone=os.getenv("TIME_ZONE", "UTC")
    )

    # Use the query variant verified to work in this tenancy (from last_60m_scan)
    qd = QueryDetails(
        query_string="* | stats count as logrecords by 'Log Source' | sort -logrecords",
        compartment_id=compartment_id,
        sub_system="LOG",
        max_total_count=5000,
        should_include_total_count=True,
        should_run_async=False,
        time_filter=time_filter,
        compartment_id_in_subtree=True,
    )

    resp = la_client.query(namespace_name=namespace, query_details=qd, limit=5000)
    data = resp.data

    # Normalize result to list of dicts with keys [source, count]
    rows: List[Dict] = []
    cols = [getattr(c, "column_name", None) or getattr(c, "name", None) or f"col_{i}" for i, c in enumerate(getattr(data, "columns", []) or [])]

    # Prefer items (dict-like); else map rows+cols
    items = getattr(data, "items", []) or []
    if items and isinstance(items, list) and isinstance(items[0], dict):
        # Identify keys heuristically
        src_key = None
        cnt_key = None
        if cols:
            for c in cols:
                cl = (c or "").lower().replace(" ", "")
                if cl in ("logsource", "source", "log_source"):
                    src_key = c
                if cl in ("logrecords", "count"):
                    cnt_key = c
        if items and not (src_key and cnt_key):
            for k in items[0].keys():
                kl = str(k).lower()
                if not src_key and ("log source" in kl or "logsource" in kl or kl == "source"):
                    src_key = k
                if not cnt_key and (kl in ("logrecords", "count") or "records" in kl):
                    cnt_key = k
        for it in items:
            src = it.get(src_key, "-") if src_key else next(iter(it.values()), "-")
            cnt = it.get(cnt_key, 0) if cnt_key else (list(it.values())[1] if len(it.values()) > 1 else 0)
            rows.append({"source": src, "count": cnt})
        return rows

    raw_rows = getattr(data, "rows", []) or []
    if raw_rows and cols:
        # Identify likely columns
        src_idx = None
        cnt_idx = None
        for i, c in enumerate(cols):
            cl = (c or "").lower().replace(" ", "")
            if src_idx is None and cl in ("logsource", "source", "log_source"):
                src_idx = i
            if cnt_idx is None and cl in ("logrecords", "count"):
                cnt_idx = i
        for r in raw_rows:
            values = getattr(r, "values", None) or getattr(r, "data", None) or []
            if values:
                src = values[src_idx] if (src_idx is not None and src_idx < len(values)) else values[0]
                cnt = values[cnt_idx] if (cnt_idx is not None and cnt_idx < len(values)) else (values[1] if len(values) > 1 else 0)
                rows.append({"source": src, "count": cnt})
    return rows


def run():
    cfg = get_oci_config()
    region = cfg.get("region")
    tenancy = cfg.get("tenancy") or os.getenv("COMPARTMENT_OCID")
    if not tenancy:
        raise RuntimeError("Unable to resolve tenancy OCID")

    # Ensure region is explicitly set (default to current or eu-frankfurt-1)
    cfg = cfg.copy()
    cfg["region"] = os.getenv("LOGAN_REGION", region or "eu-frankfurt-1")

    identity = oci.identity.IdentityClient(cfg)
    la = oci.log_analytics.LogAnalyticsClient(cfg)
    ns = os.getenv("LA_NAMESPACE") or resolve_namespace(la, tenancy)

    comps = list_all_compartments(identity, tenancy)

    print(f"Logging Analytics Namespace: {ns}")
    print(f"Region: {cfg['region']}")
    print(f"Scanning {len(comps)} compartments (including tenancy root) for last 24h")
    print("")
    print("| Compartment | Log Source | Events (last 24h) |")
    print("|-------------|------------|-------------------:|")

    any_printed = False
    for name, cid in comps:
        try:
            rows = query_sources_last_24h(la, ns, cid)
            for r in rows[:100]:  # limit per compartment
                print(f"| {name} | {r['source']} | {r['count']} |")
                any_printed = True
        except oci.exceptions.ServiceError as e:
            # Ignore not authorized/not found on some compartments
            if getattr(e, "status", None) in (401, 403, 404):
                continue
            continue

    if not any_printed:
        print("| (no sources found) | - | 0 |")


if __name__ == "__main__":
    run()
