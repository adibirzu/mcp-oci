# OCI Resource Manager Server

Exposes `oci:resourcemanager:*` tools.

## Tools
- `oci:resourcemanager:list-stacks` — List stacks in a compartment.
- `oci:resourcemanager:get-stack` — Get a stack by OCID.
- `oci:resourcemanager:list-jobs` — List jobs in a compartment or for a stack.

## Parameters
- list-stacks: `compartment_id` (required), `limit?`, `page?`.
- get-stack: `stack_id` (required).
- list-jobs: `compartment_id?`, `stack_id?`, `limit?`, `page?`.

## Responses
- Responses include `opc_request_id` and `next_page` where available.
## Usage
Serve:
```
mcp-oci-serve-resourcemanager --profile DEFAULT --region us-phoenix-1
```
