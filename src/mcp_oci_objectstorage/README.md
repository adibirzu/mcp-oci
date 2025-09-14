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
- `oci:objectstorage:get-namespace` — Retrieve object storage namespace.
- `oci:objectstorage:list-buckets` — List buckets in a namespace/compartment.
- `oci:objectstorage:list-objects` — List objects in a bucket.
 - `oci:objectstorage:get-bucket` — Get bucket details.
 - `oci:objectstorage:list-preauth-requests` — List preauthenticated requests.
 - `oci:objectstorage:create-preauth-request` — Mutating. Create PAR (confirm/dry_run supported).

## Usage
Serve:
```
mcp-oci-serve-objectstorage --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call objectstorage oci:objectstorage:get-namespace
mcp-oci call objectstorage oci:objectstorage:list-buckets --params '{"namespace_name":"axxx","compartment_id":"ocid1.compartment..."}'
mcp-oci call objectstorage oci:objectstorage:get-bucket --params '{"namespace_name":"axxx","bucket_name":"demo"}'
mcp-oci call objectstorage oci:objectstorage:list-preauth-requests --params '{"namespace_name":"axxx","bucket_name":"demo"}'
\# Dry run then confirm a mutating call
mcp-oci call objectstorage oci:objectstorage:create-preauth-request --params '{"namespace_name":"axxx","bucket_name":"demo","name":"tmp","access_type":"ObjectRead","time_expires":"2025-12-31T23:59:59Z","dry_run":true}'
mcp-oci call objectstorage oci:objectstorage:create-preauth-request --params '{"namespace_name":"axxx","bucket_name":"demo","name":"tmp","access_type":"ObjectRead","time_expires":"2025-12-31T23:59:59Z","confirm":true}'
```

### Example Host Config (MCP)
```json
{
  "mcpServers": {
    "oci-objectstorage": {
      "command": "mcp-oci-serve-objectstorage",
      "args": ["--profile", "DEFAULT", "--region", "us-phoenix-1"]
    }
  }
}
```

### Example Transcript
```
> tools/call name=oci:objectstorage:list-objects arguments={"namespace_name":"axxx","bucket_name":"demo"}
< { "content": [ { "type": "json", "json": { "items": [ { "name": "foo.txt" } ] } } ] }
```

## Next
See ../../docs/SERVERS.md for all OCI MCP servers.
