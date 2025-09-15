# OCI File Storage Server

Exposes `oci:filestorage:*` tools.

## Tools
- `oci:filestorage:list-file-systems` — List File Systems (AD required).
- `oci:filestorage:list-mount-targets` — List Mount Targets (AD required).

## Usage
Serve:
```
mcp-oci-serve-filestorage --profile DEFAULT --region eu-frankfurt-1
```

## Parameters
- list-file-systems: `compartment_id` (required), `availability_domain` (required), `limit?`, `page?`.
- list-mount-targets: `compartment_id` (required), `availability_domain` (required), `limit?`, `page?`.

## Responses
- Responses include `opc_request_id` and `next_page` where available.
