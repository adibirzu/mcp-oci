# OCI Usage API Server

Exposes `oci:usageapi:*` tools for cost and usage analytics.

## Tools
- `oci:usageapi:request-summarized-usages` — Request summarized usage or cost.
- `oci:usageapi:cost-by-service` — Convenience wrapper: COST grouped by service for last N days.
- `oci:usageapi:cost-by-compartment` — Convenience wrapper: COST grouped by compartmentId for last N days.
- `oci:usageapi:usage-by-service` — Convenience wrapper: USAGE grouped by service for last N days.
- `oci:usageapi:usage-by-compartment` — Convenience wrapper: USAGE grouped by compartmentId for last N days.
- `oci:usageapi:list-rate-cards` — List rate cards (list price) for a subscription.

## Usage
Serve:
```
mcp-oci-serve-usageapi --profile DEFAULT --region us-phoenix-1
```
Dev call:
```
mcp-oci call usageapi oci:usageapi:request-summarized-usages --params '{"tenant_id":"ocid1.tenancy...","time_usage_started":"2025-01-01T00:00:00Z","time_usage_ended":"2025-01-31T23:59:59Z","granularity":"DAILY","query_type":"COST","group_by":["service"]}'
```

## Parameters
- request-summarized-usages: `tenant_id` (required), `time_usage_started` (required), `time_usage_ended` (required), `granularity?`, `query_type?`, `group_by?`.
  - Note: For `DAILY`/`MONTHLY`, times must be midnight UTC (YYYY-MM-DDT00:00:00Z). This server normalizes times to midnight when granularity is DAILY/MONTHLY.
  - Optional server-side filters: `dimensions?` (e.g., `{ "service": "Compute" }`), `tags?`.
- cost-by-service: `tenant_id` (required), `days?` (default 7), `granularity?` (default DAILY).
- cost-by-compartment: `tenant_id` (required), `days?` (default 7), `granularity?` (default DAILY).
- usage-by-service: `tenant_id` (required), `days?` (default 7), `granularity?` (default DAILY).
- usage-by-compartment: `tenant_id` (required), `days?` (default 7), `granularity?` (default DAILY).
 - list-rate-cards: `subscription_id` (required), `time_from?`, `time_to?`, `part_number?` (client-side filter).

## Troubleshooting
- Ensure the profile has permissions to call Usage API.
- Use correct time window; empty results often indicate an empty or incorrect range.
- If you hit "UTC date does not have the right precision" errors, ensure times are at midnight UTC. The wrappers handle this automatically.
- Wrappers apply optional client-side filters when `service_name` or `compartment_id` are provided.
- Dimensions filter support depends on SDK model availability (Filter); if unsupported by your SDK version, filters are ignored.

## Rate Cards (List Price)
- See the how-to for a full walkthrough: `howto/rate-cards`.
- Common fields returned by `list-rate-cards` (shape may vary by subscription):
  - `partNumber` — product part number (e.g., "B90906").
  - `rate` — list price per unit (numeric).
  - `unit` — billing unit (e.g., "OCPU_HOUR", "GB_MONTH").
  - `currency` — currency code for the rate (e.g., "USD").
  - `timeFrom` / `timeTo` — validity window for the rate.

Example output (abridged):
```
{
  "items": [
    {
      "partNumber": "B90906",
      "rate": 0.025,
      "unit": "GB_MONTH",
      "currency": "USD",
      "timeFrom": "2025-01-01T00:00:00Z"
    }
  ]
}
```
