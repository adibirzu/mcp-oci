# mcp_oci_iam

## Overview
OCI Identity and Access Management MCP server. Exposes read-focused tools (`oci:iam:*`) following AWS MCP best practices.

## Installation
```
make setup
```

## Configuration
Uses OCI SDK with `~/.oci/config` or env vars. Optional defaults via `mcp-oci-serve --profile <p> --region <r>`.

## Tools / Resources
- `oci_iam_list_users` — List users in a compartment.
- `oci_iam_get_user` — Get a user by OCID.
- `oci_iam_list_compartments` — List compartments; supports subtree and access level.
- `oci_iam_list_groups` — List groups.
- `oci_iam_list_policies` — List policies.
 - `oci_iam_list_user_groups` — List a user’s group memberships; optional group expansion.
 - `oci_iam_list_policy_statements` — Flatten policy statements across policies.
 - `oci_iam_list_api_keys` — List API keys for a user.
 - `oci_iam_add_user_to_group` — Mutating. Add user to group (confirm/dry_run supported).

## Usage
Serve over stdio (for MCP hosts):
```
mcp-oci-serve iam --profile DEFAULT --region us-phoenix-1
```
Dev call examples:
```
mcp-oci call iam oci_iam_list_users --params '{"compartment_id":"ocid1.tenancy..."}'
mcp-oci call iam oci_iam_get_user --params '{"user_id":"ocid1.user..."}'
mcp-oci call iam oci_iam_list_user_groups --params '{"compartment_id":"ocid1.tenancy...","user_id":"ocid1.user...","include_groups":true}'
mcp-oci call iam oci_iam_list_policy_statements --params '{"compartment_id":"ocid1.tenancy..."}'
\# API keys
mcp-oci call iam oci_iam_list_api_keys --params '{"user_id":"ocid1.user..."}'
\# Dry run then confirm a mutating call
mcp-oci call iam oci_iam_add_user_to_group --params '{"user_id":"ocid1.user...","group_id":"ocid1.group...","dry_run":true}'
mcp-oci call iam oci_iam_add_user_to_group --params '{"user_id":"ocid1.user...","group_id":"ocid1.group...","confirm":true}'
```

### Example Host Config (MCP)
```json
{
  "mcpServers": {
    "oci-iam": {
      "command": "mcp-oci-serve",
      "args": ["iam", "--profile", "DEFAULT", "--region", "us-phoenix-1", "--log-level", "INFO"]
    }
  }
}
```

### Example Transcript
```
> tools/list
< [ { "name": "oci:iam:list-users" }, { "name": "oci:iam:get-user" }, ... ]
> tools/call name=oci:iam:get-user arguments={"user_id":"ocid1.user..."}
< { "content": [ { "type": "json", "json": { "item": { "id": "ocid1.user...", "lifecycle_state": "ACTIVE" } } } ] }
```

## Development
Run tests and linters:
```
make test && make lint
```

## Next
See ../../docs/SERVERS.md for all OCI MCP servers.
