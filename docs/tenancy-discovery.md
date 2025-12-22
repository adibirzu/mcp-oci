# Tenancy Discovery

MCP-OCI automatically discovers and caches tenancy information at server startup to optimize performance and reduce API calls.

## Overview

Tenancy discovery runs automatically when:
- Installing MCP-OCI (`./scripts/install.sh`)
- Starting MCP servers (`scripts/mcp-launchers/start-mcp-server.sh`)

The discovery process collects:
- Tenancy details (name, ID, description)
- Home region
- Subscribed regions
- Compartment hierarchy (top-level compartments)

## Cache Location

Tenancy discovery cache is stored at:
```
~/.mcp-oci/cache/tenancy_discovery.json
```

You can customize the cache directory with:
```bash
export MCP_CACHE_DIR="/path/to/cache"
```

## Cache Format

The cache file contains:
```json
{
  "id": "[Link to Secure Variable: OCI_TENANCY_OCID]",
  "name": "MyTenancy",
  "description": "Tenancy description",
  "home_region": "us-ashburn-1",
  "subscribed_regions": [
    {
      "name": "us-ashburn-1",
      "key": "IAD",
      "is_home": true,
      "status": "READY"
    }
  ],
  "compartments": [
    {
      "id": "[Link to Secure Variable: OCI_COMPARTMENT_OCID]",
      "name": "root",
      "description": "Root compartment",
      "lifecycle_state": "ACTIVE",
      "is_root": true
    }
  ],
  "discovered_at": "2024-01-15T10:30:00Z"
}
```

## Manual Discovery

You can run tenancy discovery manually:

```bash
python scripts/init_tenancy_discovery.py
```

This will:
1. Discover tenancy information from OCI
2. Save cache to `~/.mcp-oci/cache/tenancy_discovery.json`
3. Print discovered information to stdout

## Using Discovery Cache

MCP servers automatically use the discovery cache when available. The cache is used by:
- Compartment resolution utilities
- Region selection helpers
- Smart resolvers for resource lookups

## Refresh Cache

The cache is refreshed:
- On server startup (automatic)
- When running `init_tenancy_discovery.py` manually
- When cache file is missing or invalid

To force a refresh:
```bash
rm ~/.mcp-oci/cache/tenancy_discovery.json
# Restart servers or run discovery manually
```

## Troubleshooting

### Discovery Fails

If discovery fails:
1. Verify OCI credentials are configured (`oci setup config`)
2. Check network connectivity to OCI
3. Verify IAM permissions (read access to tenancy and compartments)
4. Check logs for specific error messages

### Cache Not Updating

If cache seems stale:
1. Delete the cache file: `rm ~/.mcp-oci/cache/tenancy_discovery.json`
2. Restart servers or run discovery manually
3. Verify write permissions to cache directory

### Missing Compartments

Discovery only fetches top-level compartments by default (first 50). For deeper hierarchies:
- Use the inventory server's `list_compartments` tool
- Run `scripts/build-local-cache.py` for comprehensive discovery

## Integration with MCP Servers

All MCP servers benefit from tenancy discovery:
- **Faster startup**: No need to query tenancy on first tool call
- **Better error messages**: Can resolve compartment names to OCIDs
- **Smart defaults**: Automatically uses home region when region not specified

## Best Practices

1. **Run discovery at startup**: Automatic via installation scripts
2. **Refresh periodically**: Cache is refreshed on server restart
3. **Monitor cache age**: Discovery includes timestamp for monitoring
4. **Use in CI/CD**: Cache discovery results for faster test runs

## Related Documentation

- [Installation Guide](../README.md#installation)
- [Configuration Guide](../README.md#configuration)
- [Architecture Guide](../ARCHITECTURE.md)
