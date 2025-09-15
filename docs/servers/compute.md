# OCI Compute Server

Exposes `oci:compute:*` tools for instances, images, and VNICs.

## Tools
- `oci:compute:list-instances` — List instances (optionally filter by `lifecycle_state`; defaults to tenancy if `compartment_id` omitted; can search subcompartments).
 - `oci:compute:list-instances` — List instances with advanced filters (defaults to tenancy if `compartment_id` omitted; can search subcompartments).
- `oci:compute:get-instance` — Get instance details.
- `oci:compute:list-images` — List images.
  - Filters: `operating_system`, `operating_system_version`.
- `oci:compute:list-vnics` — List VNIC attachments for an instance.
- `oci:compute:list-shapes` — List shapes.
- `oci:compute:instance-action` — Mutating. START/STOP/RESET (confirm/dry_run).
- `oci:compute:list-boot-volumes` — List boot volumes (Blockstorage).
- `oci:compute:list-instance-configurations` — List instance configurations (Compute Management).
- `oci:compute:list-boot-volume-attachments` — List boot volume attachments.
- `oci:compute:search-instances` — Search instances via OCI Resource Search (structured queries).
- `oci:compute:list-stopped-instances` — Convenience alias that lists STOPPED instances and prompts to narrow scope.

## Usage
Serve:
```
mcp-oci-serve-compute --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call compute oci:compute:list-instances --params '{"lifecycle_state":"STOPPED"}'
mcp-oci call compute oci:compute:list-instances --params '{"compartment_name":"prod", "display_name_contains":"web", "time_created_after":"2025-01-01T00:00:00Z"}'
mcp-oci call compute oci:compute:list-shapes --params '{"compartment_id":"ocid1.compartment..."}'
mcp-oci call compute oci:compute:list-images --params '{"compartment_id":"ocid1.compartment...","operating_system":"Oracle Linux","operating_system_version":"9"}'
\# Mutating example
mcp-oci call compute oci:compute:instance-action --params '{"instance_id":"ocid1.instance...","action":"STOP","dry_run":true}'
\# Search examples
mcp-oci call compute oci:compute:search-instances --params '{"lifecycle_state":"STOPPED"}'
mcp-oci call compute oci:compute:search-instances --params '{"display_name":"web-01","compartment_id":"ocid1.compartment...","include_subtree":true}'
\# Alias: STOPPED with guidance
mcp-oci call compute oci:compute:list-stopped-instances --params '{"compartment_name":"adrian_birzu","include_subtree":true}'
```

## Parameters
- list-instances: `compartment_id?` (defaults to tenancy), `compartment_name?` (resolve to id), `availability_domain?`, `lifecycle_state?` (e.g., STOPPED), `include_subtree?` (default true), `display_name?`, `display_name_contains?`, `shape?`, `time_created_after?`, `time_created_before?`, `freeform_tags?` (map), `defined_tags?` (map of `namespace.key` -> value), `limit?`, `page?`, `max_items?` (cap aggregated results).
- search-instances: `query?` (structured), `lifecycle_state?`, `display_name?`, `compartment_id?`, `include_subtree?` (default true), `limit?`, `page?`.
- list-stopped-instances: same filters as `list-instances` (without `lifecycle_state` which is forced to STOPPED); returns `hints` suggesting `compartment_name/time_created_after/before` when results are large or empty.
- list-images: `compartment_id` (required), `operating_system?`, `operating_system_version?`, `limit?`, `page?`, `image_id?`.
- list-boot-volumes: `compartment_id` (required), `availability_domain` (required), `limit?`, `page?`.
- list-instance-configurations: `compartment_id` (required), `limit?`, `page?`.
- instance-action: `instance_id` (required), `action` (required), `dry_run?`, `confirm?`.
- list-boot-volume-attachments: `compartment_id?`, `instance_id?`, `availability_domain?`, `limit?`, `page?`.

## Troubleshooting
- 404 or empty: verify compartment, AD, and region.
- 401/403: ensure profile has permissions for Compute/Blockstorage.
- Instance action blocked: ensure instance in a valid lifecycle state for the action.
## Responses
- Handlers attach `opc_request_id` and `next_page` when available.
Example:
```
{
  "items": [ { "id": "ocid1.instance...", "shape": "VM.Standard.E5.Flex" } ],
  "next_page": null,
  "opc_request_id": "EFGH5678..."
}
```
