"""
Optimized FastMCP Server Entry Point
Clear, Claude-friendly responses with auto-discovery
"""

import argparse
import sys
from typing import Optional

from .loganalytics import run_loganalytics_optimized
from .iam import run_iam_optimized


def main():
    parser = argparse.ArgumentParser(description="MCP OCI FastMCP Optimized Server")
    parser.add_argument("service", choices=[
        "loganalytics", "iam"
    ], help="Service to serve")
    parser.add_argument("--profile", default="DEFAULT", help="OCI profile")
    parser.add_argument("--region", help="OCI region")
    parser.add_argument("--server-name", help="Server name")

    args = parser.parse_args()

    if args.service == "loganalytics":
        run_loganalytics_optimized(
            profile=args.profile, 
            region=args.region, 
            server_name=args.server_name or "oci-loganalytics-optimized"
        )
    elif args.service == "iam":
        run_iam_optimized(
            profile=args.profile, 
            region=args.region, 
            server_name=args.server_name or "oci-iam-optimized"
        )


if __name__ == "__main__":
    main()
