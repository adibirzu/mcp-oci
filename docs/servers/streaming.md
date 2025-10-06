# OCI Streaming Server

Exposes `oci:streaming:*` tools for Oracle Cloud Infrastructure Streaming service.

## Tools

### `oci:streaming:list-streams`
List streams in a compartment.

**Parameters:**
- `compartment_id` (string, required): The OCID of the compartment
- `name` (string, optional): Filter by stream name
- `limit` (integer, optional): Maximum number of results to return
- `page` (string, optional): Pagination token
- `profile` (string, optional): OCI profile name
- `region` (string, optional): OCI region

**Example:**
```json
{
  "compartment_id": "ocid1.compartment.oc1..example",
  "limit": 10
}
```

### `oci:streaming:get-stream`
Get stream details by OCID.

**Parameters:**
- `stream_id` (string, required): The OCID of the stream
- `profile` (string, optional): OCI profile name
- `region` (string, optional): OCI region

**Example:**
```json
{
  "stream_id": "ocid1.stream.oc1..example"
}
```

## Usage

### Standard Server
```bash
mcp-oci-serve-streaming --profile DEFAULT --region us-phoenix-1
```

### FastMCP Server (Recommended)
```bash
python -m mcp_oci_fastmcp streaming --profile DEFAULT --region us-phoenix-1
```

## Configuration

The server uses standard OCI configuration via:
- `~/.oci/config` file
- Environment variables: `OCI_TENANCY`, `OCI_USER`, `OCI_REGION`, etc.

## Error Handling

The server provides comprehensive error handling with:
- Detailed error messages
- Graceful degradation
- Retry mechanisms for transient failures

## Security

- Uses OCI IAM for authentication
- Respects compartment-level access controls
- No hardcoded credentials