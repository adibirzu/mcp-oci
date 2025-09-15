# OCI Database Server

Exposes `oci:database:*` tools.

## Usage
Serve:
```
mcp-oci-serve-database --profile DEFAULT --region us-phoenix-1
```
## Tools
- `oci:database:list-autonomous-databases` — List ADBs in a compartment.
- `oci:database:list-db-systems` — List DB Systems.
- `oci:database:list-backups` — List DB backups.
 - `oci:database:list-databases` — List databases filtered by compartment or DB Home.

## Parameters
- list-autonomous-databases: `compartment_id` (required), `lifecycle_state?`, `limit?`, `page?`.
- list-db-systems: `compartment_id` (required), `lifecycle_state?`, `limit?`, `page?`.
- list-backups: `compartment_id` (required), `db_system_id?`, `database_id?`, `lifecycle_state?`, `limit?`, `page?`.
 - list-databases: `compartment_id?`, `db_home_id?`, `limit?`, `page?`.

## Responses
- Responses include `opc_request_id` and pagination `next_page` when available.
Example:
```
{
  "items": [ { "dbName": "ADB1", "lifecycleState": "AVAILABLE" } ],
  "next_page": null,
  "opc_request_id": "..."
}
```
