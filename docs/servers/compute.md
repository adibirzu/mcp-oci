# OCI Compute Server

Exposes `oci:compute:*` tools for instances, images, and VNICs.

## Tools
- `oci:compute:list-instances` — List instances in a compartment.
- `oci:compute:get-instance` — Get instance details.
- `oci:compute:list-images` — List images.
  - Filters: `operating_system`, `operating_system_version`.
- `oci:compute:list-vnics` — List VNIC attachments for an instance.
- `oci:compute:list-shapes` — List shapes.
- `oci:compute:instance-action` — Mutating. START/STOP/RESET (confirm/dry_run).
 - `oci:compute:list-boot-volumes` — List boot volumes (Blockstorage).
 - `oci:compute:list-instance-configurations` — List instance configurations (Compute Management).

## Usage
Serve:
```
mcp-oci-serve-compute --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call compute oci:compute:list-shapes --params '{"compartment_id":"ocid1.compartment..."}'
mcp-oci call compute oci:compute:list-images --params '{"compartment_id":"ocid1.compartment...","operating_system":"Oracle Linux","operating_system_version":"9"}'
\# Mutating example
mcp-oci call compute oci:compute:instance-action --params '{"instance_id":"ocid1.instance...","action":"STOP","dry_run":true}'
```

## Parameters
- list-images: `compartment_id` (required), `operating_system?`, `operating_system_version?`, `limit?`, `page?`.
- list-boot-volumes: `compartment_id` (required), `availability_domain` (required), `limit?`, `page?`.
- list-instance-configurations: `compartment_id` (required), `limit?`, `page?`.
- instance-action: `instance_id` (required), `action` (required), `dry_run?`, `confirm?`.

## Troubleshooting
- 404 or empty: verify compartment, AD, and region.
- 401/403: ensure profile has permissions for Compute/Blockstorage.
- Instance action blocked: ensure instance in a valid lifecycle state for the action.
