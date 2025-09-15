# OCI API Gateway Server

Exposes `oci:apigateway:*` tools.

## Usage
Serve:
```
mcp-oci-serve-apigateway --profile DEFAULT --region us-phoenix-1
```
# OCI API Gateway Server

Exposes `oci:apigateway:*` tools.

## Tools
- `oci:apigateway:list-gateways` — List API Gateways in a compartment.
- `oci:apigateway:get-gateway` — Get API Gateway by OCID.

## Usage
Serve:
```
mcp-oci-serve-apigateway --profile DEFAULT --region eu-frankfurt-1
```

## Parameters
- list-gateways: `compartment_id` (required), `display_name?`, `limit?`, `page?`.
- get-gateway: `gateway_id` (required).

## Responses
- Responses include `opc_request_id` and `next_page` where available.
