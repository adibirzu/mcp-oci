Archived scripts

The following scripts are deprecated and no longer used in the MCP servers deployment flow. They remain in the repo for historical reference but exit immediately with guidance.

- deploy_full_aiops.sh — replaced by unified launcher and Linux install guide
- deploy_aiops_agent.sh — replaced by unified launcher and UX controls
- deploy.sh — replaced by unified launcher
- start-observability-macos.sh — macOS helper no longer needed
- vendor_oracle_examples.sh — vendoring examples is not part of deploy
- generate_wallet.py — use official Oracle tooling for DB wallets
- provision_ajd.py — provision via OCI Console/Terraform
- populate_db_from_mcp.py — demo-only data loader

Use these instead:
- scripts/mcp-launchers/start-mcp-server.sh — start/stop/status for all MCP servers
- scripts/smoke_check.py — verify all servers are healthy and privacy masking is active

See README for Linux installation instructions.

