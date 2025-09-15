# OCI Load Balancer Server

Exposes `oci:loadbalancer:*` tools.

## Tools
- `oci:loadbalancer:list-load-balancers` — List Load Balancers in a compartment.
- `oci:loadbalancer:get-backend-health` — Get backend set health.

## Usage
Serve:
```
mcp-oci-serve-loadbalancer --profile DEFAULT --region eu-frankfurt-1
```

## Parameters
- list-load-balancers: `compartment_id` (required), `limit?`, `page?`.
- get-backend-health: `load_balancer_id` (required), `backend_set_name` (required).

## Responses
- Responses include `opc_request_id` and `next_page` when available.
