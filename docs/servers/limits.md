# OCI Limits and Quotas Server

Exposes `oci:limits:*` and `oci:quotas:*` tools for service limits and compartment quotas.

## Tools
- `oci:limits:list-services` — List services with limits in a compartment.
- `oci:limits:list-limit-values` — List limit values for a service.
- `oci:quotas:list-quotas` — List quotas in a compartment.
- `oci:quotas:get-quota` — Get quota by OCID.

## Usage
Serve:
```
mcp-oci-serve-limits --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call limits oci:limits:list-services --params '{"compartment_id":"ocid1.compartment..."}'
mcp-oci call limits oci:limits:list-limit-values --params '{"compartment_id":"ocid1.compartment...","service_name":"compute","scope_type":"REGION"}'
```

## Parameters
- list-services: `compartment_id` (required), `limit?`, `page?`.
- list-limit-values: `compartment_id` (required), `service_name` (required), `scope_type?`, `availability_domain?`, `limit?`, `page?`.
- list-quotas: `compartment_id` (required), `limit?`, `page?`.
- get-quota: `quota_id` (required).

## Troubleshooting
- 404/empty: confirm region and service_name for limits.
- Permissions: ensure profile has Limits/Quotas read permissions.
