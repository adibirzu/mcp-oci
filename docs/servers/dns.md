# OCI DNS Server

Exposes `oci:dns:*` tools.

## Tools
- `oci:dns:list-zones` — List zones in a compartment.
- `oci:dns:list-rrset` — List RRSet for a zone and domain; optional record type filter.

## Usage
Serve:
```
mcp-oci-serve-dns --profile DEFAULT --region eu-frankfurt-1
```

## Parameters
- list-zones: `compartment_id` (required), `limit?`, `page?`.
- list-rrset: `zone_name_or_id` (required), `domain` (required), `rtype?`.

## Responses
- Responses include `opc_request_id` and `next_page` where available.
