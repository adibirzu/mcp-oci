"""
FastMCP REST API Server Entry Point
Optimized for minimal token usage with direct REST API calls
"""

import argparse
import sys
from typing import Optional

from .compute import run_compute_rest
from .iam import run_iam_rest
from .objectstorage import run_objectstorage_rest
from .networking import run_networking_rest
from .database import run_database_rest
from .loganalytics import run_loganalytics_rest


def main():
    parser = argparse.ArgumentParser(description="MCP OCI FastMCP REST API Server")
    parser.add_argument("service", choices=[
        "compute", "iam", "objectstorage", "networking", "database", "loganalytics"
    ], help="Service to serve")
    parser.add_argument("--profile", default="DEFAULT", help="OCI profile")
    parser.add_argument("--region", help="OCI region")
    parser.add_argument("--server-name", help="Server name")

    args = parser.parse_args()

    if args.service == "compute":
        run_compute_rest(profile=args.profile, region=args.region, server_name=args.server_name or "oci-compute-rest")
    elif args.service == "iam":
        run_iam_rest(profile=args.profile, region=args.region, server_name=args.server_name or "oci-iam-rest")
    elif args.service == "objectstorage":
        run_objectstorage_rest(profile=args.profile, region=args.region, server_name=args.server_name or "oci-objectstorage-rest")
    elif args.service == "networking":
        run_networking_rest(profile=args.profile, region=args.region, server_name=args.server_name or "oci-networking-rest")
    elif args.service == "database":
        run_database_rest(profile=args.profile, region=args.region, server_name=args.server_name or "oci-database-rest")
    elif args.service == "loganalytics":
        run_loganalytics_rest(profile=args.profile, region=args.region, server_name=args.server_name or "oci-loganalytics-rest")


if __name__ == "__main__":
    main()
