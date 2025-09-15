import argparse
import sys
from typing import Optional

from .compute import run_compute
from .iam import run_iam
from .usageapi import run_usageapi
from .monitoring import run_monitoring
from .networking import run_networking
from .objectstorage import run_objectstorage
from .database import run_database
from .blockstorage import run_blockstorage
from .oke import run_oke
from .functions import run_functions
from .vault import run_vault
from .loadbalancer import run_loadbalancer
from .dns import run_dns
from .kms import run_kms
from .events import run_events
from .streaming import run_streaming
from .loganalytics import run_loganalytics
from .server_proper import app as proper_app
from .server_optimized import app as optimized_app
from .compute_optimized import run_compute as run_compute_optimized
from .iam_optimized import run_iam as run_iam_optimized
from .loganalytics_optimized import run_loganalytics as run_loganalytics_optimized
from .objectstorage_optimized import run_objectstorage as run_objectstorage_optimized
from .networking_optimized import run_networking as run_networking_optimized
from .database_optimized import run_database as run_database_optimized
from .monitoring_optimized import run_monitoring as run_monitoring_optimized
from .usageapi_optimized import run_usageapi as run_usageapi_optimized
from .blockstorage_optimized import run_blockstorage as run_blockstorage_optimized
from .oke_optimized import run_oke as run_oke_optimized
from .functions_optimized import run_functions as run_functions_optimized
from .vault_optimized import run_vault as run_vault_optimized
from .loadbalancer_optimized import run_loadbalancer as run_loadbalancer_optimized
from .dns_optimized import run_dns as run_dns_optimized
from .kms_optimized import run_kms as run_kms_optimized
from .events_optimized import run_events as run_events_optimized
from .streaming_optimized import run_streaming as run_streaming_optimized


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
        run_compute(profile=args.profile, region=args.region, server_name=args.server_name or "oci-compute-fast")
    elif args.service == "iam":
        run_iam(profile=args.profile, region=args.region, server_name=args.server_name or "oci-iam-fast")
    elif args.service == "usageapi":
        run_usageapi(profile=args.profile, region=args.region, server_name=args.server_name or "oci-usageapi-fast")
    elif args.service == "monitoring":
        run_monitoring(profile=args.profile, region=args.region, server_name=args.server_name or "oci-monitoring-fast")
    elif args.service == "networking":
        run_networking(profile=args.profile, region=args.region, server_name=args.server_name or "oci-networking-fast")
    elif args.service == "objectstorage":
        run_objectstorage(profile=args.profile, region=args.region, server_name=args.server_name or "oci-objectstorage-fast")
    elif args.service == "database":
        run_database(profile=args.profile, region=args.region, server_name=args.server_name or "oci-database-fast")
    elif args.service == "blockstorage":
        run_blockstorage(profile=args.profile, region=args.region, server_name=args.server_name or "oci-blockstorage-fast")
    elif args.service == "oke":
        run_oke(profile=args.profile, region=args.region, server_name=args.server_name or "oci-oke-fast")
    elif args.service == "functions":
        run_functions(profile=args.profile, region=args.region, server_name=args.server_name or "oci-functions-fast")
    elif args.service == "vault":
        run_vault(profile=args.profile, region=args.region, server_name=args.server_name or "oci-vault-fast")
    elif args.service == "loadbalancer":
        run_loadbalancer(profile=args.profile, region=args.region, server_name=args.server_name or "oci-loadbalancer-fast")
    elif args.service == "dns":
        run_dns(profile=args.profile, region=args.region, server_name=args.server_name or "oci-dns-fast")
    elif args.service == "kms":
        run_kms(profile=args.profile, region=args.region, server_name=args.server_name or "oci-kms-fast")
    elif args.service == "events":
        run_events(profile=args.profile, region=args.region, server_name=args.server_name or "oci-events-fast")
    elif args.service == "streaming":
        run_streaming(profile=args.profile, region=args.region, server_name=args.server_name or "oci-streaming-fast")
    elif args.service == "loganalytics":
        run_loganalytics(profile=args.profile, region=args.region, server_name=args.server_name or "oci-loganalytics-fast")
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
    elif args.service == "compute":
        run_compute_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_compute")
    elif args.service == "iam":
        run_iam_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_iam")
    elif args.service == "loganalytics":
        run_loganalytics_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_loganalytics")
    elif args.service == "objectstorage":
        run_objectstorage_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_objectstorage")
    elif args.service == "networking":
        run_networking_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_networking")
    elif args.service == "database":
        run_database_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_database")
    elif args.service == "monitoring":
        run_monitoring_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_monitoring")
    elif args.service == "usageapi":
        run_usageapi_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_usageapi")
    elif args.service == "blockstorage":
        run_blockstorage_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_blockstorage")
    elif args.service == "oke":
        run_oke_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_oke")
    elif args.service == "functions":
        run_functions_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_functions")
    elif args.service == "vault":
        run_vault_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_vault")
    elif args.service == "loadbalancer":
        run_loadbalancer_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_loadbalancer")
    elif args.service == "dns":
        run_dns_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_dns")
    elif args.service == "kms":
        run_kms_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_kms")
    elif args.service == "events":
        run_events_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_events")
    elif args.service == "streaming":
        run_streaming_optimized(profile=args.profile, region=args.region, server_name=args.server_name or "mcp_oci_streaming")
    elif args.service == "all":
        # Run the all-in-one optimized server
        optimized_app.run()
    else:
        print(f"Unsupported service: {args.service}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
