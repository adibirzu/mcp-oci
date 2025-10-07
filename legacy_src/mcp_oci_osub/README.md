# mcp_oci_osub

## Overview
OCI Subscriptions (OSUB) MCP server. Use it to discover subscription IDs for your tenancy.

## Tools / Resources
- `oci_osub_list_subscriptions` — List subscriptions for `tenancy_id`.

## Usage
```
mcp-oci-serve osub --profile DEFAULT --region eu-frankfurt-1
mcp-oci call osub oci_osub_list_subscriptions --params '{"tenancy_id":"ocid1.tenancy..."}'
```

## Next
See docs/howto/rate-cards.md for retrieving list prices (rate cards).
