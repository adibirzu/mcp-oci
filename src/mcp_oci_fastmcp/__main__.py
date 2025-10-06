import argparse
import sys

from .blockstorage import run_blockstorage
from .compute import run_compute
from .database import run_database
from .dns import run_dns
from .events import run_events
from .functions import run_functions
from .iam import run_iam
from .kms import run_kms
from .loadbalancer import run_loadbalancer
from .loganalytics import run_loganalytics
from .monitoring import run_monitoring
from .networking import run_networking
from .objectstorage import run_objectstorage
from .oke import run_oke
from .server import app as optimized_app
from .server_proper import app as proper_app
from .streaming import run_streaming
from .usageapi import run_usageapi
from .vault import run_vault


def main() -> None:
    p = argparse.ArgumentParser(description="Serve OCI MCP via FastMCP framework")
    p.add_argument("service", choices=[
        "compute", "iam", "usageapi", "monitoring", "networking", "objectstorage",
        "database", "blockstorage", "oke", "functions", "vault", "loadbalancer",
        "dns", "kms", "events", "streaming", "loganalytics", "proper", "optimized",
        "all"
    ], help="Service to serve")
    p.add_argument("--profile")
    p.add_argument("--region")
    p.add_argument("--server-name", default=None)
    args = p.parse_args()

    if args.service == "compute":
        run_compute(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_compute")
    elif args.service == "iam":
        run_iam(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_iam")
    elif args.service == "usageapi":
        run_usageapi(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_usageapi")
    elif args.service == "monitoring":
        run_monitoring(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_monitoring")
    elif args.service == "networking":
        run_networking(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_networking")
    elif args.service == "objectstorage":
        run_objectstorage(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_objectstorage")
    elif args.service == "database":
        run_database(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_database")
    elif args.service == "blockstorage":
        run_blockstorage(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_blockstorage")
    elif args.service == "oke":
        run_oke(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_oke")
    elif args.service == "functions":
        run_functions(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_functions")
    elif args.service == "vault":
        run_vault(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_vault")
    elif args.service == "loadbalancer":
        run_loadbalancer(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_loadbalancer")
    elif args.service == "dns":
        run_dns(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_dns")
    elif args.service == "kms":
        run_kms(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_kms")
    elif args.service == "events":
        run_events(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_events")
    elif args.service == "streaming":
        run_streaming(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_streaming")
    elif args.service == "loganalytics":
        run_loganalytics(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_loganalytics")
    elif args.service == "proper":
        # Run the proper implementation
        proper_app.run()
    elif args.service == "optimized":
        # Set environment variables if provided
        if args.profile:
            import os
            os.environ["OCI_PROFILE"] = args.profile
        if args.region:
            import os
            os.environ["OCI_REGION"] = args.region
        # Run the optimized implementation
        optimized_app.run()
    elif args.service == "all":
        # Run the all-in-one optimized server
        optimized_app.run()
    else:
        print(f"Unsupported service: {args.service}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()