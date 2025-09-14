# How-To: Retrieve OCI List Prices (Rate Cards)

This guide shows how to discover your subscription IDs and retrieve list prices (rate cards) for OCI services.

## 1) Find Subscription IDs (OSUB)
Serve the OSUB server and list subscriptions for your tenancy:
```
mcp-oci-serve-osub --profile DEFAULT --region eu-frankfurt-1
mcp-oci call osub oci:osub:list-subscriptions --params '{"tenancy_id":"ocid1.tenancy..."}'
```
Copy a `subscriptionId` from the output.

## 2) List Rate Cards (Usage API)
With a subscription ID, list rate cards:
```
mcp-oci-serve-usageapi --profile DEFAULT --region eu-frankfurt-1
mcp-oci call usageapi oci:usageapi:list-rate-cards --params '{"subscription_id":"ocid1.subscription..."}'
```
Optional filters:
- Time window: `time_from`, `time_to` (midnight UTC recommended); example: `"2025-01-01T00:00:00Z"`
- Part number: `part_number` for client-side filtering

## Notes
- Permissions: ensure your profile has OSUB and Usage API permissions.
- Regions: use your home region for OSUB; Usage API endpoints are regional.
