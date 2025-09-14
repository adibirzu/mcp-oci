# OCI Budgets Server

Exposes `oci:budgets:*` tools for cost control.

## Tools
- `oci:budgets:list-budgets` — List budgets in a compartment.
- `oci:budgets:get-budget` — Get a budget by OCID.
- `oci:budgets:list-alert-rules` — List alert rules for a budget.
- `oci:budgets:create-budget` — Mutating. Create budget (confirm/dry_run).

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

## Parameters
- list-budgets: `compartment_id` (required), `limit?`, `page?`.
- get-budget: `budget_id` (required).
- list-alert-rules: `budget_id` (required), `limit?`, `page?`.
- create-budget: `compartment_id` (required), `amount` (required), `reset_period?`, `display_name?`, `targets?`, `dry_run?`, `confirm?`.

## Troubleshooting
- 401/403: ensure profile has Budgets permissions.
- Create budget fails: verify compartment target and currency configuration in tenancy.
