#!/usr/bin/env python3
"""
Generate Autonomous Database wallet zip to a target path.

Env/Args:
  COMPARTMENT_OCID (or --compartment)
  DISPLAY_NAME (or --display-name) of the target Autonomous DB (AJD)
  WALLET_PASSWORD (or --wallet-password) for the wallet zip
  OUTPUT_ZIP (or --output-zip) target path
  PROFILE/REGION optional
"""
from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate wallet zip for Autonomous DB")
    parser.add_argument("--compartment", default=os.getenv("COMPARTMENT_OCID"))
    parser.add_argument("--display-name", default=os.getenv("DISPLAY_NAME", "aiops-ajd"))
    parser.add_argument("--wallet-password", default=os.getenv("WALLET_PASSWORD") or os.getenv("ORACLE_DB_WALLET_PASSWORD"))
    parser.add_argument("--output-zip", default=os.getenv("OUTPUT_ZIP") or os.getenv("ORACLE_DB_WALLET_ZIP"))
    parser.add_argument("--profile", default=os.getenv("OCI_PROFILE", "DEFAULT"))
    parser.add_argument("--region", default=os.getenv("OCI_REGION"))
    args = parser.parse_args()

    if not args.compartment or not args.wallet_password or not args.output_zip:
        print("ERROR: COMPARTMENT_OCID, WALLET_PASSWORD, OUTPUT_ZIP required", file=sys.stderr)
        sys.exit(2)

    import oci
    cfg = oci.config.from_file(profile_name=args.profile)
    if args.region:
        cfg["region"] = args.region
    db = oci.database.DatabaseClient(cfg)

    # Locate database by display name and workload AJD
    resp = db.list_autonomous_databases(compartment_id=args.compartment, db_workload="AJD")
    targets = [ad for ad in resp.data if getattr(ad, 'display_name', None) == args.display_name]
    if not targets:
        print(f"ERROR: No AJD found with display name {args.display_name}", file=sys.stderr)
        sys.exit(3)
    ad = targets[0]
    # Generate wallet
    wallet_details = oci.database.models.GenerateAutonomousDatabaseWalletDetails(password=args.wallet_password)
    wallet_resp = db.generate_autonomous_database_wallet(ad.id, generate_autonomous_database_wallet_details=wallet_details)
    content = wallet_resp.data.content
    with open(args.output_zip, 'wb') as f:
        f.write(content)
    print(f"Wallet written to {args.output_zip}")

if __name__ == "__main__":
    main()

