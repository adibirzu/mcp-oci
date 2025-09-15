# OCI Events Server

Exposes `oci:events:*` tools.

## Tools
- `oci:events:list-rules` — List Event Rules in a compartment.
- `oci:events:get-rule` — Get Event Rule by OCID.

## Usage
Serve:
```
mcp-oci-serve-events --profile DEFAULT --region eu-frankfurt-1
```

## Parameters
- list-rules: `compartment_id` (required), `lifecycle_state?`, `limit?`, `page?`.
- get-rule: `rule_id` (required).

## Responses
- Responses include `opc_request_id` and `next_page` where available.
