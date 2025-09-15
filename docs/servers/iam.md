# OCI IAM Server

Exposes `oci:iam:*` tools for Identity and Access Management.

## Tools
- `oci:iam:list-users` — List users in a compartment.
  - Filter: `name` (exact match).
- `oci:iam:get-user` — Get a user by OCID.
- `oci:iam:list-compartments` — List compartments; supports subtree and access level.
- `oci:iam:list-groups` — List groups.
- `oci:iam:list-policies` — List policies.
 - `oci:iam:list-user-groups` — List user group memberships; optional group expansion.
- `oci:iam:list-policy-statements` — Flatten policy statements.
- `oci:iam:list-api-keys` — List API keys for a user.
- `oci:iam:list-dynamic-groups` — List dynamic groups in a compartment.
- `oci:iam:list-auth-tokens` — List auth tokens for a user.
- `oci:iam:add-user-to-group` — Mutating. Add user to group (confirm/dry_run).

## Usage
Serve over stdio:
```
mcp-oci-serve-iam --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call iam oci:iam:list-users --params '{"compartment_id":"ocid1.tenancy..."}'
mcp-oci call iam oci:iam:list-user-groups --params '{"compartment_id":"ocid1.tenancy...","user_id":"ocid1.user...","include_groups":true}'
mcp-oci call iam oci:iam:list-policy-statements --params '{"compartment_id":"ocid1.tenancy..."}'
\# API Keys
mcp-oci call iam oci:iam:list-api-keys --params '{"user_id":"ocid1.user..."}'
\# Mutating example (dry run then confirm)
mcp-oci call iam oci:iam:add-user-to-group --params '{"user_id":"ocid1.user...","group_id":"ocid1.group...","dry_run":true}'
mcp-oci call iam oci:iam:add-user-to-group --params '{"user_id":"ocid1.user...","group_id":"ocid1.group...","confirm":true}'
```

## Parameters
- list-users: `compartment_id` (required), `name?`, `limit?`, `page?`.
- list-user-groups: `compartment_id` (required), `user_id` (required), `include_groups?`, `limit?`, `page?`.
- list-policy-statements: `compartment_id` (required), `limit?`, `page?`.
- list-api-keys: `user_id` (required).
- add-user-to-group: `user_id` (required), `group_id` (required), `dry_run?`, `confirm?`.
- list-compartments: `compartment_id` (required), `include_subtree?` (default true), `access_level?` (ANY or ACCESSIBLE), `limit?`, `page?`.

## Troubleshooting
- 404 or empty: verify tenancy OCID, user OCID, and region.
- 401/403: profile lacks permissions for IAM read/write operations.
- Name filter returns nothing: `name` is exact match; check case and spelling.
## Responses
- Responses include `opc_request_id` when available (useful for Oracle support) and pagination tokens like `next_page`.
Example (abridged):
```
{
  "items": [ { "id": "ocid1.user...", "lifecycle_state": "ACTIVE" } ],
  "next_page": null,
  "opc_request_id": "ABCD1234..."
}
```
