# OCI Subscriptions (OSUB) Server

Exposes `oci:osub:*` tools to discover subscriptions for a tenancy.

## Tools
- `oci:osub:list-subscriptions` — List subscriptions for a tenancy (tenancy_id).

## Usage
Serve:
```
mcp-oci-serve-osub --profile DEFAULT --region eu-frankfurt-1
```
Dev call:
```
mcp-oci call osub oci:osub:list-subscriptions --params '{"tenancy_id":"ocid1.tenancy..."}'
```

## Parameters
- list-subscriptions: `tenancy_id` (required), `limit?`, `page?`.

## Troubleshooting
- 401/403: ensure profile has permissions for OSUB APIs.
- Some regions may not provide OSUB endpoints; use your home region.
