# mcp_oci_limits

## Overview
OCI Limits and Quotas MCP server. Read service limits and compartment quotas.

## Installation
```
make setup
```

## Tools / Resources
- `oci_limits_list_services` — List services with limits in a compartment.
- `oci_limits_list_limit_values` — List limit values for a service.
- `oci_quotas_list_quotas` — List quotas in a compartment.
- `oci_quotas_get_quota` — Get quota by OCID.

## Usage
Serve:
```
mcp-oci-serve limits --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call limits oci_limits_list_services --params '{"compartment_id":"ocid1.compartment..."}'
mcp-oci call limits oci_limits_list_limit_values --params '{"compartment_id":"ocid1.compartment...","service_name":"compute","scope_type":"REGION"}'
```

## Next
See ../../docs/SERVERS.md for all OCI MCP servers.
