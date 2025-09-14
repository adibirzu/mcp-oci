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
- `oci:networking:list-vcns` — List VCNs in a compartment.
- `oci:networking:list-vcns-by-dns` — Filter VCNs by `dns_label` (client-side filter).
- `oci:networking:list-subnets` — List subnets; optional VCN filter.
- `oci:networking:list-route-tables` — List route tables; optional VCN filter.
- `oci:networking:list-security-lists` — List security lists; optional VCN filter.
- `oci:networking:create-vcn` — Mutating. Create VCN (confirm/dry_run supported).

## Usage
Serve:
```
mcp-oci-serve-networking --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call networking oci:networking:list-vcns --params '{"compartment_id":"ocid1.compartment..."}'
mcp-oci call networking oci:networking:list-vcns-by-dns --params '{"compartment_id":"ocid1.compartment...","dns_label":"demo"}'
\# Dry run then confirm a mutating call
mcp-oci call networking oci:networking:create-vcn --params '{"compartment_id":"ocid1.compartment...","cidr_block":"10.0.0.0/16","display_name":"demo","dry_run":true}'
```

## Next
See ../../docs/SERVERS.md for all OCI MCP servers.
