#!/usr/bin/env python3
import json
import sys
import traceback
from datetime import datetime

try:
    import oci
    from oci.pagination import list_call_get_all_results
except Exception as e:
    print(f"ERROR: Failed to import OCI SDK: {e}", file=sys.stderr)
    sys.exit(1)

try:
    # Reuse project helpers if available
    from mcp_oci_common import get_oci_config
except Exception:
    # Fallback to direct config file read
    def get_oci_config():
        return oci.config.from_file()

def fetch_all_compartments(identity_client, tenancy_id: str):
    """
    Returns a list of active compartment OCIDs including the root tenancy.
    """
    try:
        comps_resp = list_call_get_all_results(
            identity_client.list_compartments,
            tenancy_id,
            compartment_id_in_subtree=True,
            access_level="ACCESSIBLE"
        )
        comp_ids = [c.id for c in comps_resp.data if getattr(c, "lifecycle_state", "ACTIVE") == "ACTIVE"]
        if tenancy_id not in comp_ids:
            comp_ids.insert(0, tenancy_id)
        return comp_ids
    except Exception as e:
        print(f"ERROR: Failed listing compartments: {e}", file=sys.stderr)
        raise

def fetch_all_regions(identity_client, tenancy_id: str):
    """
    Returns a list of subscribed region names for the tenancy.
    """
    try:
        subs = identity_client.list_region_subscriptions(tenancy_id).data
        return [s.region_name for s in subs]
    except Exception as e:
        print(f"ERROR: Failed listing region subscriptions: {e}", file=sys.stderr)
        raise

def list_instances_across_tenancy():
    cfg = get_oci_config()
    tenancy_id = cfg["tenancy"]

    identity = oci.identity.IdentityClient(cfg)

    regions = fetch_all_regions(identity, tenancy_id)
    compartments = fetch_all_compartments(identity, tenancy_id)

    inventory = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "tenancy_id": tenancy_id,
        "region_count": len(regions),
        "compartment_count": len(compartments),
        "instances": []
    }

    total = 0
    for region in regions:
        cfg_r = dict(cfg)
        cfg_r["region"] = region
        compute = oci.core.ComputeClient(cfg_r)

        for comp_id in compartments:
            try:
                resp = list_call_get_all_results(compute.list_instances, compartment_id=comp_id)
                for inst in resp.data:
                    total += 1
                    inventory["instances"].append({
                        "region": region,
                        "compartment_id": comp_id,
                        "id": getattr(inst, "id", ""),
                        "display_name": getattr(inst, "display_name", ""),
                        "lifecycle_state": getattr(inst, "lifecycle_state", ""),
                        "shape": getattr(inst, "shape", ""),
                        "availability_domain": getattr(inst, "availability_domain", ""),
                        "time_created": getattr(inst, "time_created", "").isoformat() if hasattr(inst, "time_created") and inst.time_created else None,
                    })
            except oci.exceptions.ServiceError as se:
                # Log and continue scanning other compartments/regions
                print(f"WARN: Failed listing instances in region {region} compartment {comp_id}: {se}", file=sys.stderr)
            except Exception as e:
                print(f"WARN: Unexpected error in region {region} compartment {comp_id}: {e}", file=sys.stderr)

    inventory["total_instances"] = total
    return inventory

def main():
    try:
        result = list_instances_across_tenancy()
        print(json.dumps(result, indent=2))
    except Exception:
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
