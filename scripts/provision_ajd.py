#!/usr/bin/env python3
"""
Provision Autonomous JSON Database (AJD) if not present.

Requires OCI Python SDK and ~/.oci/config or instance principals.

Env/Args:
- COMPARTMENT_OCID (or --compartment)
- DISPLAY_NAME (or --display-name)
- DB_NAME (or --db-name) – 14 chars max, letters only
- ADMIN_PASSWORD (or --admin-password) – meets OCI complexity
- PROFILE (--profile), REGION (--region)

Example:
  scripts/provision_ajd.py --compartment ocid1.compartment... --display-name aiops-ajd --db-name AIOPSAJD --admin-password 'Your#P@ssw0rd1'
"""
from __future__ import annotations

import argparse
import os
import sys

def main() -> None:
    parser = argparse.ArgumentParser(description="Provision Autonomous JSON DB if missing")
    parser.add_argument("--compartment", default=os.getenv("COMPARTMENT_OCID"))
    parser.add_argument("--display-name", default=os.getenv("DISPLAY_NAME", "aiops-ajd"))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "AIOPSAJD"))
    parser.add_argument("--admin-password", default=os.getenv("ADMIN_PASSWORD"))
    parser.add_argument("--profile", default=os.getenv("OCI_PROFILE", "DEFAULT"))
    parser.add_argument("--region", default=os.getenv("OCI_REGION"))
    args = parser.parse_args()

    if not args.compartment or not args.admin_password:
        print("ERROR: COMPARTMENT_OCID and ADMIN_PASSWORD are required.", file=sys.stderr)
        sys.exit(2)

    import oci

    cfg = oci.config.from_file(profile_name=args.profile)
    if args.region:
        cfg["region"] = args.region

    db = oci.database.DatabaseClient(cfg)
    # Check existing databases by display name
    existing = []
    try:
        resp = db.list_autonomous_databases(compartment_id=args.compartment, db_workload="AJD")
        existing = [ad for ad in resp.data if getattr(ad, 'display_name', None) == args.display_name]
    except Exception as e:
        print(f"WARN: list_autonomous_databases failed: {e}")

    if existing:
        print(f"Found existing AJD: {existing[0].id}")
        return

    details = oci.database.models.CreateAutonomousDatabaseDetails(
        compartment_id=args.compartment,
        db_name=args.db_name,
        display_name=args.display_name,
        admin_password=args.admin_password,
        db_workload="AJD",
        is_auto_scaling_enabled=True,
        is_dedicated=False,
        data_storage_size_in_tbs=1,
        cpu_core_count=1,
        is_free_tier=True,
    )

    print(f"Creating AJD '{args.display_name}' in {args.compartment} ...")
    resp = db.create_autonomous_database(details)
    ad = resp.data
    print(f"Create initiated. OCID: {ad.id}")

if __name__ == "__main__":
    main()

