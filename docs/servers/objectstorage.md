# OCI Object Storage Server

Exposes `oci:objectstorage:*` tools.

## Tools
- `oci:objectstorage:get-namespace` — Get namespace.
- `oci:objectstorage:list-buckets` — List buckets.
- `oci:objectstorage:list-objects` — List objects.
- `oci:objectstorage:get-bucket` — Get bucket details.
- `oci:objectstorage:list-preauth-requests` — List preauthenticated requests.
- `oci:objectstorage:create-preauth-request` — Mutating. Create PAR (confirm/dry_run).
- `oci:objectstorage:head-object` — Get object metadata (HEAD).

## Usage
Serve:
```
mcp-oci-serve-objectstorage --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call objectstorage oci:objectstorage:get-bucket --params '{"namespace_name":"axxx","bucket_name":"demo"}'
\# Mutating example
mcp-oci call objectstorage oci:objectstorage:create-preauth-request --params '{"namespace_name":"axxx","bucket_name":"demo","name":"tmp","access_type":"ObjectRead","time_expires":"2025-12-31T23:59:59Z","dry_run":true}'
```

## Responses
- Responses include `opc_request_id` and, for list endpoints, `next_page` or `next_start_with`.
Example:
```
{
  "items": [ { "name": "my-bucket", "timeCreated": "..." } ],
  "next_page": null,
  "opc_request_id": "IJKL9012..."
}
```
## Parameters
- get-namespace: `compartment_id?`.
- list-buckets: `namespace_name` (required), `compartment_id` (required), `limit?`, `page?`.
- list-objects: `namespace_name` (required), `bucket_name` (required), `prefix?`, `start?`, `limit?`.
- get-bucket: `namespace_name` (required), `bucket_name` (required).
- list-preauth-requests: `namespace_name` (required), `bucket_name` (required), `object_name?`, `limit?`, `page?`.
- create-preauth-request: `namespace_name` (required), `bucket_name` (required), `name` (required), `access_type` (required), `time_expires` (required), `object_name?`, `dry_run?`, `confirm?`.
- head-object: `namespace_name` (required), `bucket_name` (required), `object_name` (required).
