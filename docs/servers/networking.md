# OCI Networking Server

Exposes `oci:networking:*` tools.

## Tools
- `oci:networking:list-subnets` — List subnets; filter by VCN.
- `oci:networking:list-vcns` — List VCNs.
- `oci:networking:list-vcns-by-dns` — Filter VCNs by dns_label.
- `oci:networking:create-vcn` — Mutating. Create VCN (confirm/dry_run).
- `oci:networking:list-route-tables` — List route tables; optional VCN filter.
- `oci:networking:list-security-lists` — List security lists; optional VCN filter.
- `oci:networking:list-network-security-groups` — List NSGs; optional VCN filter.

## Usage
Serve:
```
mcp-oci-serve-networking --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call networking oci:networking:list-vcns --params '{"compartment_id":"ocid1.compartment..."}'
\# Filter by dns_label
mcp-oci call networking oci:networking:list-vcns-by-dns --params '{"compartment_id":"ocid1.compartment...","dns_label":"demo"}'
\# Mutating example
mcp-oci call networking oci:networking:create-vcn --params '{"compartment_id":"ocid1.compartment...","cidr_block":"10.0.0.0/16","display_name":"demo","dry_run":true}'
```

## Parameters
- list-subnets: `compartment_id` (required), `vcn_id?`, `limit?`, `page?`, `profile?`, `region?`.
- list-vcns: `compartment_id` (required), `limit?`, `page?`, `profile?`, `region?`.
- list-vcns-by-dns: `compartment_id` (required), `dns_label` (required), `limit?`, `page?`.
- list-route-tables: `compartment_id` (required), `vcn_id?`, `limit?`, `page?`.
- list-security-lists: `compartment_id` (required), `vcn_id?`, `limit?`, `page?`.
- create-vcn: `compartment_id`, `cidr_block`, `display_name` (required); `dns_label?`, `dry_run?`, `confirm?`.
  - Performance: list-vcns/list-subnets/list-security-lists cache results and update name→OCID mappings to reduce repeated calls. Subsequent lookups by name (e.g., filtering flows) can be resolved without extra API requests.

## Responses
- Responses include `opc_request_id` and pagination tokens where available.

## Troubleshooting
- 404 or empty results: verify compartment OCID and region.
- 401/403: check OCI credentials/profile permissions for Networking.
- Throttling: add pagination (`limit`) and retry with backoff.
