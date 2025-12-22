# Object Storage MCP Server Runbook (oci-mcp-objectstorage)

Use this runbook for bucket inventory, usage reporting, and backup artifact lookup.

## Inputs
- Compartment OCID or name
- Namespace (if not default)
- Bucket name or prefix (optional)

## Steps
1. **List buckets in scope**
   - Tool: `list_buckets`
2. **Inspect a specific bucket**
   - Tool: `get_bucket`
3. **List objects or backup artifacts**
   - Tools: `list_objects`, `list_db_backups`
4. **Summarize usage and storage cost drivers**
   - Tools: `get_bucket_usage`, `get_storage_report`
5. **Create a pre-authenticated request if requested**
   - Tool: `create_preauthenticated_request`

## Skill/Tool mapping
- Inventory: `list_buckets`, `list_objects`
- Usage: `get_bucket_usage`, `get_storage_report`
- Backup lookup: `list_db_backups`, `get_backup_details`
- Access: `create_preauthenticated_request`

## Outputs
- Bucket/object inventory
- Usage summary and top buckets
- PAR confirmation when created
