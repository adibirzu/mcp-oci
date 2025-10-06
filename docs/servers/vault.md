# OCI Vault Server

Exposes `oci:vault:*` tools for Oracle Cloud Infrastructure Vault (Secrets) service.

## Tools

### `oci:vault:list-secrets`
List secrets in a compartment.

**Parameters:**
- `compartment_id` (string, required): The OCID of the compartment
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

### `oci:vault:get-secret-bundle`
Get the latest secret bundle by secret OCID.

**Parameters:**
- `secret_id` (string, required): The OCID of the secret
- `profile` (string, optional): OCI profile name
- `region` (string, optional): OCI region

**Example:**
```json
{
  "secret_id": "ocid1.vaultsecret.oc1..example"
}
```

## Usage

### Standard Server
```bash
mcp-oci-serve-vault --profile DEFAULT --region us-phoenix-1
```

### FastMCP Server (Recommended)
```bash
python -m mcp_oci_fastmcp vault --profile DEFAULT --region us-phoenix-1
```

## Configuration

The server uses standard OCI configuration via:
- `~/.oci/config` file
- Environment variables: `OCI_TENANCY`, `OCI_USER`, `OCI_REGION`, etc.

## Security

- Uses OCI IAM for authentication
- Respects compartment-level access controls
- No hardcoded credentials
- Secret values are handled securely

## Error Handling

The server provides comprehensive error handling with:
- Detailed error messages
- Graceful degradation
- Retry mechanisms for transient failures