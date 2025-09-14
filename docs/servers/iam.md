# OCI IAM Server

Exposes `oci:iam:*` tools for Identity and Access Management.

## Tools
- `oci:iam:list-users` — List users in a compartment.
- `oci:iam:get-user` — Get a user by OCID.
- `oci:iam:list-compartments` — List compartments; supports subtree and access level.
- `oci:iam:list-groups` — List groups.
- `oci:iam:list-policies` — List policies.

## Usage
Serve over stdio:
```
mcp-oci-serve-iam --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call iam oci:iam:list-users --params '{"compartment_id":"ocid1.tenancy..."}'
```
