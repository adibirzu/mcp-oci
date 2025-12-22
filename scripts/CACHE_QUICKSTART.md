# Local Cache Quick Start Guide

## 1. Build Your First Cache (2 minutes)

```bash
# Navigate to project root
cd <REPO_ROOT>

# Run cache builder
python scripts/build-local-cache.py
```

You should see output like:
```
INFO - Collecting tenancy details...
INFO - Tenancy: MyTenancy (Home: us-ashburn-1)
INFO - Collecting compartment hierarchy...
INFO - Collected 12 compartments
INFO - Collecting compute resources...
INFO - Collected 45 compute instances
INFO - Collecting database resources...
INFO - Collected 5 DB systems and 3 autonomous databases
INFO - Collecting users and groups...
INFO - Collected 23 users and 7 groups
INFO - Collecting network resources...
INFO - Collected 15 VCNs and 52 subnets
INFO - Cache building complete!

============================================================
OCI LOCAL CACHE SUMMARY
============================================================
Generated at: 2025-11-19T13:45:00.123456+00:00
Tenancy: MyTenancy
Home Region: us-ashburn-1
Compartments: 12
Compute Instances: 45
Databases: 8
Users: 23
Groups: 7
Network Resources: 67
============================================================
```

## 2. Verify Cache

```bash
# Check cache files exist
ls -lah ~/.mcp-oci/cache/

# View metadata
cat ~/.mcp-oci/cache/cache_metadata.json
```

## 2b. (Optional) Redis Shared Cache

```bash
# Store cache in Redis for shared access
export MCP_CACHE_BACKEND=redis
export MCP_REDIS_URL=redis://localhost:6379
export MCP_CACHE_KEY_PREFIX=mcp:cache
python scripts/build-local-cache.py
```

## 3. Use Enhanced Servers

### Start Cost Server

```bash
# The cost server will automatically use the cache
python -m mcp_servers.cost.server
```

### Test New Tools

From your MCP client (e.g., Claude Desktop):

```javascript
// Get tenancy information
await mcpClient.call_tool("get_tenancy_info", {});

// Check cache statistics
await mcpClient.call_tool("get_cache_stats", {});

// Refresh cache
await mcpClient.call_tool("refresh_local_cache", {});
```

## 4. Schedule Automatic Refresh

```bash
# Edit crontab
crontab -e

# Add this line to refresh every 6 hours
0 */6 * * * cd <REPO_ROOT> && python scripts/build-local-cache.py >> ~/.mcp-oci/cache/refresh.log 2>&1
```

## Common Options

```bash
# Use specific profile
python scripts/build-local-cache.py --profile PRODUCTION

# Use specific region
python scripts/build-local-cache.py --region us-phoenix-1

# Custom cache directory
python scripts/build-local-cache.py --cache-dir /custom/path

# Enable debug output
python scripts/build-local-cache.py --debug
```

## What Gets Cached?

- ✅ Compartment hierarchy (all compartments)
- ✅ Compute instances (display names, shapes, states)
- ✅ Database systems (DB systems + Autonomous DBs)
- ✅ Network resources (VCNs, subnets)
- ✅ IAM users and groups
- ✅ Tenancy details (name, regions)

## What Doesn't Get Cached?

- ❌ Cost/usage data (always fetched live)
- ❌ Secrets or credentials
- ❌ Real-time metrics
- ❌ Resource configurations (security rules, etc.)

## Cache Age Recommendations

- **Development**: Refresh daily
- **Production**: Refresh every 6 hours
- **Large Tenancies**: Refresh every 12 hours

## Troubleshooting

### "Cache file not found"
```bash
# Build cache for first time
python scripts/build-local-cache.py
```

### "OCI authentication failed"
```bash
# Verify OCI config
oci iam region list

# Test with specific profile
python scripts/build-local-cache.py --profile MYPROFILE
```

### "Permission denied"
```bash
# Create cache directory
mkdir -p ~/.mcp-oci/cache
chmod 700 ~/.mcp-oci/cache
```

## Next Steps

1. Read the [full documentation](../docs/LOCAL_CACHE_ENHANCEMENT.md)
2. Explore new MCP tools in your client
3. Set up automatic refresh
4. Monitor token usage reduction

## Support

Questions? See:
- [LOCAL_CACHE_ENHANCEMENT.md](../docs/LOCAL_CACHE_ENHANCEMENT.md) - Full documentation
- [GitHub Issues](https://github.com/adibirzu/mcp-oci/issues) - Report issues
