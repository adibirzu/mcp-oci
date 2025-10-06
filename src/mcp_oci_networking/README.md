# mcp_oci_networking

## Overview
OCI Networking MCP server. Provides read tools for VCNs and subnets; includes a confirm-gated create VCN tool.

## Installation
```
make setup
```

## Configuration
Use `~/.oci/config` or env vars; pass defaults via serve flags.

## Tools / Resources
- `oci_networking_list_vcns` — List VCNs in a compartment.
- `oci_networking_list_vcns_by_dns` — Filter VCNs by `dns_label` (client-side filter).
- `oci_networking_list_subnets` — List subnets; optional VCN filter.
- `oci_networking_list_route_tables` — List route tables; optional VCN filter.
- `oci_networking_list_security_lists` — List security lists; optional VCN filter.
- `oci_networking_create_vcn` — Mutating. Create VCN (confirm/dry_run supported).

## Usage
Serve:
```
mcp-oci-serve networking --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call networking oci_networking_list_vcns --params '{"compartment_id":"ocid1.compartment..."}'
mcp-oci call networking oci_networking_list_vcns_by_dns --params '{"compartment_id":"ocid1.compartment...","dns_label":"demo"}'
\# Dry run then confirm a mutating call
mcp-oci call networking oci_networking_create_vcn --params '{"compartment_id":"ocid1.compartment...","cidr_block":"10.0.0.0/16","display_name":"demo","dry_run":true}'
```

## Next
See ../../docs/SERVERS.md for all OCI MCP servers.
