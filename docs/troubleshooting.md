# Troubleshooting

Quick pointers for common issues and where to look. See client‑specific guides for exact configuration steps.

Common errors
- spawn ENOENT: The MCP client cannot find the server binary. Fix by using an absolute path to your venv binary (e.g., `/path/to/repo/.venv/bin/mcp-oci-serve-iam`), or ensure your venv bin is on PATH for the GUI app. Docker is an alternative.
- Could not connect / Server disconnected: Start the server manually with `--log-level DEBUG` to see stderr. Verify credentials with `mcp-oci doctor` and confirm `--profile` and `--region`.
- 401/403 Authorization: The OCI profile lacks permissions. Validate the tenancy, user/instance principal, and policies.
- 404/Empty results: Check compartment OCIDs, region mismatches, and filters (e.g., `name` is exact match).

Where to look
- Claude Desktop logs (macOS): `~/Library/Logs/Claude/` (e.g., `mcp-server-oci-iam.log`, `mcp.log`).
- Run servers directly to debug: `mcp-oci-serve <service> --profile <PROFILE> --region <REGION> --log-level DEBUG`.

Client‑specific guides
- Claude Desktop: See `clients/claude-desktop` for config examples, PATH notes, and log locations.
- Cursor: See `clients/cursor` for MCP settings and Docker args.
- Cline (VS Code): See `clients/cline` for configuration and Docker usage.

If issues persist
- Confirm scripts exist: `.venv/bin/mcp-oci-serve-<service>` after `make setup`.
- Reinstall in the active environment: `pip install -e .[dev]`.
- Share the error snippet and client logs for targeted help.
