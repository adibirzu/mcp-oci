# Oracle Example Integrations (showusage, showoci)

This repo can integrate with Oracle's example tools to expand capabilities:
- showusage: cost/usage CLI (https://github.com/oracle/oci-python-sdk/tree/master/examples/showusage)
- showoci: inventory and reporting (https://github.com/oracle/oci-python-sdk/tree/master/examples/showoci)

## Setup
- Clone the oci-python-sdk repo locally or vendor the examples under `third_party/oci-python-sdk/examples/...`.
- Or set env vars to point to the scripts:
  - `SHOWUSAGE_PATH=/path/to/showusage.py`
  - `SHOWOCI_PATH=/path/to/showoci.py`

## MCP Tools
- Usage API server:
  - `oci:usageapi:showusage-run` — runs showusage and returns stdout. Params: `start`, `end`, `granularity?`, `groupby?`, `extra_args?`, `expect_json?`, `profile?`, `region?`, `path?`.
    - When `expect_json=true`, the server tries to parse JSON from stdout or fallback to key:value lines.
- Inventory server:
  - `oci:inventory:showoci-scan` — runs showoci and returns stdout. Params: `regions?`, `profile?`, `tenancy?`, `path?`, `extra_args?`, `expect_json?`.
    - When `expect_json=true`, the server tries to parse JSON from stdout or fallback to key:value lines.

## Notes
- Output formats depend on the upstream scripts; prefer JSON when available (pass script-specific JSON flags in `extra_args`).
- Ensure your OCI config/profile has required permissions.
