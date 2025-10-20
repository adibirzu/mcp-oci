# mcp_oci_objectstorage

## Overview
OCI Object Storage MCP server. Provides namespace, bucket, and object listing tools.

## Installation
```
make setup
```

## Configuration
Use `~/.oci/config` or env vars; pass defaults via serve flags.

## Tools / Resources
- `oci_objectstorage_get_namespace` — Retrieve object storage namespace.
- `oci_objectstorage_list_buckets` — List buckets in a namespace/compartment.
- `oci_objectstorage_list_objects` — List objects in a bucket.
 - `oci_objectstorage_get_bucket` — Get bucket details.
 - `oci_objectstorage_list_preauth_requests` — List preauthenticated requests.
 - `oci_objectstorage_create_preauth_request` — Mutating. Create PAR (confirm/dry_run supported).

## Usage
Serve:
```
mcp-oci-serve objectstorage --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call objectstorage oci_objectstorage_get_namespace
mcp-oci call objectstorage oci_objectstorage_list_buckets --params '{"namespace_name":"axxx","compartment_id":"ocid1.compartment..."}'
mcp-oci call objectstorage oci_objectstorage_get_bucket --params '{"namespace_name":"axxx","bucket_name":"demo"}'
mcp-oci call objectstorage oci_objectstorage_list_preauth_requests --params '{"namespace_name":"axxx","bucket_name":"demo"}'
\# Dry run then confirm a mutating call
mcp-oci call objectstorage oci_objectstorage_create_preauth_request --params '{"namespace_name":"axxx","bucket_name":"demo","name":"tmp","access_type":"ObjectRead","time_expires":"2025-12-31T23:59:59Z","dry_run":true}'
mcp-oci call objectstorage oci_objectstorage_create_preauth_request --params '{"namespace_name":"axxx","bucket_name":"demo","name":"tmp","access_type":"ObjectRead","time_expires":"2025-12-31T23:59:59Z","confirm":true}'
```

### Example Host Config (MCP)
```json
{
  "mcpServers": {
    "oci-objectstorage": {
      "command": "mcp-oci-serve",
      "args": ["objectstorage", "--profile", "DEFAULT", "--region", "us-phoenix-1"]
    }
  }
}
```

### Example Transcript
```
> tools/call name=oci_objectstorage_list_objects arguments={"namespace_name":"axxx","bucket_name":"demo"}
< { "content": [ { "type": "json", "json": { "items": [ { "name": "foo.txt" } ] } } ] }
```

## Next
See ../../docs/SERVERS.md for all OCI MCP servers.
