# OCI Security (Well-Architected) Server

Aggregates security posture from Cloud Guard, Security Zones, Vulnerability Scanning, KMS, and IAM.

## Tools
- `oci:security:list-cloud-guard-problems` — List Cloud Guard problems; filter by `risk_level`, `lifecycle_detail`.
- `oci:security:list-security-zones` — List Security Zones in a compartment.
- `oci:security:list-host-scan-results` — List VSS host scan results.
- `oci:security:list-container-scan-results` — List VSS container scan results.
- `oci:security:list-kms-keys` — List KMS keys for a vault using its management endpoint.
- `oci:security:summary` — High-level summary counts across services.

## Usage
Serve:
```
mcp-oci-serve-security --profile DEFAULT --region eu-frankfurt-1
```
Examples:
```
mcp-oci call security oci:security:list-cloud-guard-problems --params '{"compartment_id":"ocid1.compartment...","risk_level":"CRITICAL"}'
mcp-oci call security oci:security:list-kms-keys --params '{"management_endpoint":"https://xxxxx-management.kms.eu-frankfurt-1.oraclecloud.com"}'
mcp-oci call security oci:security:summary --params '{"compartment_id":"ocid1.compartment..."}'
```

## Notes
- Some services may require enabling (e.g., Cloud Guard) or appropriate policies.
- KMS `management_endpoint` can be obtained from your Vault details in the console.

## Parameters
- list-cloud-guard-problems: `compartment_id` (required), `risk_level?`, `lifecycle_detail?`, `limit?`, `page?`.
- list-security-zones: `compartment_id` (required), `limit?`, `page?`.
- list-host-scan-results: `compartment_id?`, `limit?`, `page?`.
- list-container-scan-results: `compartment_id?`, `limit?`, `page?`.
- list-kms-keys: `management_endpoint` (required), `compartment_id?`, `limit?`, `page?`.
- summary: `compartment_id` (required), `management_endpoint?`.

## Responses
- Responses include `opc_request_id` and `next_page` when available.
