# Servers Overview & Quick Start Tools

This page highlights commonly used servers and a starter tool for each.

IAM
- Tool: `oci:iam:list-users`
- Example: `mcp-oci call iam oci:iam:list-users --params '{"compartment_id":"ocid1.tenancy..."}'`

Compute
- Tool: `oci:compute:list-instances`
- Example: `mcp-oci call compute oci:compute:list-instances --params '{"compartment_id":"ocid1.compartment..."}'`

Object Storage
- Tool: `oci:objectstorage:list-buckets`
- Example: `mcp-oci call objectstorage oci:objectstorage:list-buckets --params '{"namespace_name":"axxx","compartment_id":"ocid1.compartment..."}'`

Monitoring
- Tool: `oci:monitoring:summarize-metrics`
- Example: `mcp-oci call monitoring oci:monitoring:summarize-metrics --params '{"compartment_id":"ocid1.compartment...","namespace":"oci_computeagent","query":"CpuUtilization[1m].mean()","start_time":"2025-01-01T00:00:00Z","end_time":"2025-01-01T01:00:00Z"}'`

Usage API
- Tool: `oci:usageapi:cost-by-service`
- Example: `mcp-oci call usageapi oci:usageapi:cost-by-service --params '{"tenant_id":"ocid1.tenancy...","days":7}'`
