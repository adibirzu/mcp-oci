# mcp_oci_loganalytics

## Overview
OCI Log Analytics MCP server (logan-api-spec 20200601). Provides query execution and catalog listings.

## Installation
```
make setup
```

## Tools / Resources
- `oci:loganalytics:run-query` — Run a query with time window and optional subsystem.
- `oci:loganalytics:list-entities` — List Log Analytics entities for a namespace.
- `oci:loganalytics:list-parsers` — List parsers.
- `oci:loganalytics:list-log-groups` — List log groups (if supported by SDK).

## Usage
Serve:
```
mcp-oci-serve-loganalytics --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call loganalytics oci:loganalytics:run-query --params '{
  "namespace_name":"mytenant",
  "query_string":"search ""error"" | stats count()",
  "time_start":"2025-01-01T00:00:00Z",
  "time_end":"2025-01-02T00:00:00Z"
}'
```

## Notes
- Method and model names differ across SDK versions; the server tries multiple options and returns a helpful error if unsupported.
- Ensure the profile has permissions for Log Analytics APIs.
