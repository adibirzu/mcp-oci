#!/usr/bin/env python3
"""
Warm the MCP OCI name registry and caches for faster, low-token operation.

Usage:
  scripts/warm_registry.py --profile DEFAULT --region eu-frankfurt-1 --compartment TENANCY_OCID --limit 10
If --compartment is omitted, the tenancy from the OCI config is used.
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Warm MCP OCI name registry and caches")
    parser.add_argument("--profile", default=os.getenv("OCI_PROFILE", "DEFAULT"))
    parser.add_argument("--region", default=os.getenv("OCI_REGION"))
    parser.add_argument("--compartment", help="Compartment OCID (defaults to tenancy)")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    # Ensure src/ is importable regardless of CWD
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_path = os.path.join(repo_root, "src")
    for p in (src_path, repo_root):
        if p not in sys.path:
            sys.path.insert(0, p)
    from mcp_oci_introspect.server import warm_services, warm_compartment, registry_report
    from mcp_oci_common.config import get_oci_config

    cfg = get_oci_config(profile_name=args.profile)
    if args.region:
        cfg["region"] = args.region
    tenancy = args.compartment or cfg.get("tenancy")

    print("Warming common services...")
    print(json.dumps(warm_services(profile=args.profile, region=args.region, compartment_id=tenancy, limit=args.limit), indent=2))
    print("\nWarming core networking/compute for the compartment...")
    print(json.dumps(warm_compartment(compartment_id=tenancy, profile=args.profile, region=args.region, limit=args.limit), indent=2))
    print("\nRegistry report:")
    print(json.dumps(registry_report(), indent=2))


if __name__ == "__main__":
    main()
