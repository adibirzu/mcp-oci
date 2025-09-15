# OCI KMS Server

Exposes `oci:kms:*` tools.

## Tools
- `oci:kms:list-keys` — List keys in a vault (management endpoint required).
- `oci:kms:list-key-versions` — List versions for a key.

## Usage
Serve:
```
mcp-oci-serve-kms --profile DEFAULT --region eu-frankfurt-1
```

## Parameters
- list-keys: `management_endpoint` (required), `compartment_id?`, `limit?`, `page?`.
- list-key-versions: `management_endpoint` (required), `key_id` (required), `limit?`, `page?`.

## Responses
- Responses include `opc_request_id` and `next_page` where available.
