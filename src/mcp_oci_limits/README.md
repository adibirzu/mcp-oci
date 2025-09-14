# mcp_oci_limits

## Overview
OCI Limits and Quotas MCP server. Read service limits and compartment quotas.

## Installation
```
make setup
```

## Tools / Resources
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

## Next
See ../../docs/SERVERS.md for all OCI MCP servers.
