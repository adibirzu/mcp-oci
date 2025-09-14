# mcp_oci_budgets

## Overview
OCI Budgets MCP server for cost control. Read budgets/alerts and create budgets with confirmation/dry-run.

## Installation
```
make setup
```

## Tools / Resources
- `oci:budgets:list-budgets` — List budgets in a compartment.
- `oci:budgets:get-budget` — Get a budget by OCID.
- `oci:budgets:list-alert-rules` — List alert rules for a budget.
- `oci:budgets:create-budget` — Mutating. Create budget (confirm/dry_run supported).

## Usage
Serve:
```
mcp-oci-serve-budgets --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call budgets oci:budgets:list-budgets --params '{"compartment_id":"ocid1.compartment..."}'
\# Mutating example
mcp-oci call budgets oci:budgets:create-budget --params '{"compartment_id":"ocid1.compartment...","amount":100.0,"display_name":"demo","dry_run":true}'
```

## Next
See ../../docs/SERVERS.md for all OCI MCP servers.
