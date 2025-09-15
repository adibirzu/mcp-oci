# OCI Functions Server

Exposes `oci:functions:*` tools.

## Usage
Serve:
```
mcp-oci-serve-functions --profile DEFAULT --region us-phoenix-1
```
## Tools
- `oci:functions:list-applications` — List applications.
- `oci:functions:list-functions` — List functions in an application.
- `oci:functions:get-application` — Get application by OCID.
- `oci:functions:get-function` — Get function by OCID.
- `oci:functions:list-triggers` — List triggers for an application (if supported by SDK).

## Parameters
- list-applications: `compartment_id` (required), `display_name?`, `limit?`, `page?`.
- list-functions: `application_id` (required), `display_name?`, `limit?`, `page?`.
- get-application: `application_id` (required).
- get-function: `function_id` (required).
- list-triggers: `application_id` (required).

## Responses
- Responses include `opc_request_id` and `next_page` when available.
