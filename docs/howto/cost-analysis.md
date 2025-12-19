# How-To: Cost Analysis Recipes

This guide shows common cost analytics using the Usage API server and the showusage integration.

## Requirements
- OCI SDK installed and configured (`~/.oci/config`) with a profile that has Usage API permissions.
- Usage API server available (local or Docker).

## Daily Costs by Service for Last Month
```
mcp-oci-serve-usageapi --profile DEFAULT --region us-phoenix-1
mcp-oci call usageapi oci:usageapi:request-summarized-usages --params '{
  "tenant_id":"[Link to Secure Variable: OCI_TENANCY_OCID]",
  "time_usage_started":"2025-01-01T00:00:00Z",
  "time_usage_ended":"2025-01-31T23:59:59Z",
  "granularity":"DAILY",
  "query_type":"COST",
  "group_by":["service"]
}'
```

## Using showusage (optional)
If Oracle's `showusage.py` is available, you can run:
```
SHOWUSAGE_PATH=/path/to/showusage.py \
mcp-oci call usageapi oci:usageapi:showusage-run --params '{
  "start":"2025-01-01T00:00:00Z",
  "end":"2025-01-31T23:59:59Z",
  "granularity":"DAILY",
  "groupby":"service",
  "expect_json":true
}'
```

## Docker usage
```
docker run --rm -it -v $HOME/.oci:/root/.oci mcp-oci mcp-oci-serve-usageapi --profile DEFAULT --region us-phoenix-1
```

## Troubleshooting
- Empty results: check the time range and tenancy OCID.
- 401/403: ensure the profile has Usage API permissions.
- In Docker, mount your `~/.oci` directory into `/root/.oci`.
