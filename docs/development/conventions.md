# Conventions & Best Practices

Parameters & validation
- Use JSON Schema (type=object) with `properties` and `required`.
- Keep names snake_case and map to SDK arg names.
- Normalize timestamps where APIs require strict precision (e.g., Usage API: midnight UTC).

Mutating actions
- Mark tools `mutating: true` and require `confirm=true`
- Support `dry_run=true` to return the payload without executing

Pagination
- Include `limit` and `page` where supported; return `next_page` in responses

Errors & outputs
- Return `{ "items": [...] }` or `{ "item": {...} }` uniformly
- Attach `opc_request_id` from SDK response headers when available
- For long-running or paginated calls, include continuation tokens (e.g., `next_page`, `next_start_with`)
- Avoid leaking secrets; redact in errors; use stderr logging for diagnostics

Client creation
- Use `mcp_oci_common.get_config` + `make_client`
- Accept `profile` and `region` parameters in handlers; default via server launcher

Naming
- Tools: `oci:<service>:<action>` (stable)
- Packages: `mcp_oci_<service>`

Docs
- README per server with Overview, Tools, Usage, Parameters, Troubleshooting
- Docusaurus pages under `docs/servers/<service>.md`
- Include a short "Responses" section with meta fields (e.g., `opc_request_id`, `next_page`) and an example JSON snippet

Introspection
- Use `mcp_oci_introspect` to list new SDK methods; add tools conditionally when methods exist
