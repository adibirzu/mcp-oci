# OCI Object Storage Server

Exposes `oci:objectstorage:*` tools.

## Tools
- `oci:objectstorage:get-namespace` — Get namespace.
- `oci:objectstorage:list-buckets` — List buckets.
- `oci:objectstorage:list-objects` — List objects.
 - `oci:objectstorage:get-bucket` — Get bucket details.
 - `oci:objectstorage:list-preauth-requests` — List preauthenticated requests.
 - `oci:objectstorage:create-preauth-request` — Mutating. Create PAR (confirm/dry_run).

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
