# OCI OKE Server

Exposes `oci:oke:*` tools.

## Usage
Serve:
```
mcp-oci-serve-oke --profile DEFAULT --region us-phoenix-1
```
## Tools
- `oci:oke:list-clusters` — List clusters in a compartment.
- `oci:oke:list-node-pools` — List node pools for a cluster.
 - `oci:oke:get-cluster` — Get cluster by OCID.
 - `oci:oke:get-node-pool` — Get node pool by OCID.

## Parameters
- list-clusters: `compartment_id` (required), `name?`, `lifecycle_state?`, `limit?`, `page?`.
- list-node-pools: `compartment_id` (required), `cluster_id` (required), `name?`, `lifecycle_state?`, `limit?`, `page?`.
 - get-cluster: `cluster_id` (required).
 - get-node-pool: `node_pool_id` (required).

## Responses
- Responses include `opc_request_id` and `next_page` when available.
