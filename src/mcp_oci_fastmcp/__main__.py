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


def main() -> None:
    p = argparse.ArgumentParser(description="Serve OCI MCP via FastMCP framework")
    p.add_argument("service", choices=[
        "compute", "iam", "usageapi", "monitoring", "networking", "objectstorage",
        "database", "blockstorage", "oke", "functions", "vault", "loadbalancer",
        "dns", "kms", "events", "streaming", "loganalytics", "proper"
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
    else:
        print(f"Unsupported service: {args.service}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
