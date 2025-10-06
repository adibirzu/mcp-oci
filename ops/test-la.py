#!/usr/bin/env python3
"""
Smoke test for OCI Logging Analytics MCP server behavior outside of MCP.

- Resolves namespace (auto or via LA_NAMESPACE)
- Runs a simple query for today's sources
- Prints first rows and the selected namespace

Usage:
  OCI_PROFILE=DEFAULT OCI_REGION=eu-frankfurt-1 python ops/test-la.py
Optional:
  export LA_NAMESPACE=your_namespace   # overrides auto-detect
"""
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import oci  # type: ignore
from mcp_oci_common.config import get_oci_config, get_compartment_id


def main():
    cfg = get_oci_config()
    region = cfg.get("region")
    tenancy = cfg.get("tenancy") or os.getenv("COMPARTMENT_OCID")
    if not tenancy:
        print("ERROR: Could not resolve tenancy OCID. Set OCI config or COMPARTMENT_OCID.", file=sys.stderr)
        sys.exit(2)

    la = oci.log_analytics.LogAnalyticsClient(cfg)

    # Namespace selection: env wins; otherwise auto detect (single namespace) or print options
    ns_env = os.getenv("LA_NAMESPACE")
    if ns_env:
        namespace = ns_env
        print(f"Namespace (env): {namespace}")
    else:
        ns_resp = la.list_namespaces(compartment_id=tenancy)
        ns_items = getattr(getattr(ns_resp, "data", None), "items", []) or []
        names = [getattr(n, "namespace_name", None) or getattr(n, "name", None) for n in ns_items]
        names = [n for n in names if n]
        if not names:
            print("ERROR: No Logging Analytics namespaces found. Is LA enabled for this tenancy?", file=sys.stderr)
            sys.exit(3)
        if len(names) > 1:
            print(f"Multiple namespaces found: {names}")
            print("Set LA_NAMESPACE=<name> and re-run to choose explicitly.")
            sys.exit(4)
        namespace = names[0]
        print(f"Namespace (auto): {namespace}")

    comp = get_compartment_id()
    if not comp:
        comp = tenancy  # default to root tenancy if COMPARTMENT_OCID not set

    # Build query details for today's window (UTC midnight -> now)
    from oci.log_analytics.models import QueryDetails
    start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = datetime.now(timezone.utc)
    query = "* | stats count as logrecords by 'Log Source' | sort -logrecords"
    qd = QueryDetails(
        query_string=query,
        compartment_id=comp,
        sub_system="LOG",
        max_total_count=200
    )

    # Execute
    resp = la.query(namespace_name=namespace, query_details=qd, limit=200)
    data = resp.data
    cols = [getattr(c, "column_name", None) or getattr(c, "name", None) or f"col_{i}" for i, c in enumerate(getattr(data, "columns", []) or [])]
    print(f"Columns: {cols}")
    print("First 10 rows:")
    for row in (getattr(data, "rows", []) or [])[:10]:
        vals = getattr(row, "values", None) or getattr(row, "data", None) or []
        if cols and len(cols) == len(vals):
            print(dict(zip(cols, vals)))
        else:
            print(vals)

    print("OK")

if __name__ == "__main__":
    main()
