# Server Developer Guide (Checklist)

Use this checklist when adding a new tool to any `mcp_oci_<service>` server.

1) Define tool spec (JSON Schema)
- Name: `oci:<service>:<action>` (stable)
- Description: 1–2 lines, actionable
- Parameters: `{ type: "object", properties: {...}, required: [...] }`
- Pagination: include `limit`, `page` when supported
- Mutations: add `mutating: true`; include `confirm` and `dry_run` params

2) Implement handler
- Signature uses keyword args matching schema
- Create client via `mcp_oci_common.make_client`
- Map SDK responses to `{ items: [...] }` or `{ item: {...} }`
- Return continuation tokens (`next_page`, `next_start_with`) if present
- Redact/avoid secrets in logs and errors

3) Add CLI entry (if needed)
- Usually not required; stdio launch uses `__main__.py` and generic `mcp-oci-serve <service>`

4) Docs
- Update `src/mcp_oci_<service>/README.md` with tool name and example
- Update `docs/servers/<service>.md` with parameters and usage

5) Tests (optional but recommended)
- Add an integration test under `tests/integration/` for read-only endpoints
- Auto-discover inputs where feasible; otherwise gate via env vars

6) Validation
- Run `make lint` and `scripts/validate_tools.py` to verify schemas and handlers
