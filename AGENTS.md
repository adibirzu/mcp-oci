# Repository Guidelines

## Skills Layer

The MCP-OCI server includes a composable skills layer following the [skillz pattern](https://github.com/intellectronica/skillz):

| Skill | Purpose | Key Methods |
|-------|---------|-------------|
| `CostAnalysisSkill` | Cost analysis, trending, optimization | `analyze_cost_trend`, `detect_anomalies`, `generate_optimization_report` |
| `InventoryAuditSkill` | Resource discovery, capacity planning | `run_full_discovery`, `generate_capacity_report`, `generate_audit_report` |
| `NetworkDiagnosticsSkill` | Network topology, security assessment | `analyze_topology`, `assess_security`, `generate_network_report` |
| `ComputeManagementSkill` | Fleet health, performance insights, rightsizing | `assess_fleet_health`, `analyze_instance_performance`, `recommend_rightsizing`, `generate_fleet_report` |
| `SecurityPostureSkill` | Cloud Guard + IAM posture analysis | `assess_cloud_guard_posture`, `assess_iam_security`, `generate_security_report` |

Skills documentation: `mcp_servers/skills/SKILLS_GUIDE.md`

## Design Guidelines (OCI MCP)
- Reference (adapted): AWS MCP Design Guidelines — https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md
- Scope per service: map servers/tools to OCI services (e.g., IAM, Compute, Object Storage) with least-privilege defaults.
- Naming: tools as `oci:<service>:<action>` (e.g., `oci:iam:list-users`); packages as `mcp_oci_<service>` (e.g., `mcp_oci_iam`). Stable identifiers; avoid breaking names.
- Behavior: deterministic, idempotent where possible; explicit confirmation for destructive actions.
- IO: validate inputs; return concise, structured errors with remediation hints. Support pagination, timeouts, and long-running operations via progress/streaming.
- Logging: redact secrets; never echo credentials or full request bodies.

## Project Structure & Module Organization
- `dev/mcp-oci-x-services/` — shared OCI clients/helpers used by servers (reuse, don’t duplicate).
- `dev/mcp-oci-x-server/` — combined dev server (extend here; do not create new servers for these).
- `src/` — production MCP server packages, one per OCI service.
- `tests/` — mirrors `src/`; unit/integration tests.
- `examples/`, `scripts/`, `docs/` — samples, tooling, and design notes.

## Build, Test, and Development Commands
Python 3.11+ and the OCI Python SDK are required: https://docs.oracle.com/en-us/iaas/api/#/
- `make setup` — create venv; install `.[dev]`.
- `make dev` — run `dev/mcp-oci-x-server` with verbose logs.
- `make test` — run `pytest` with coverage.
- `make lint` / `make fmt` — Ruff/Black; auto-format.
Without Makefile: `python -m venv .venv && source .venv/bin/activate && pip install -e .[dev] && pytest -q`.

## Coding Style & Naming Conventions
- Python: 4 spaces, type hints required, public APIs documented.
- Lint/format/type-check: Ruff, Black, MyPy. Run `make lint fmt` before pushing.
- File/package names match service boundaries (e.g., `mcp_oci_objectstorage`).

## Testing Guidelines
- Pytest tests mirror `src/` (`test_<module>.py`); ≥80% coverage on changed code.
- Include OCI error paths, pagination, and throttling scenarios.
- No live network by default; use fakes or VCR.py cassettes.

## Commit & Pull Request Guidelines
- Conventional Commits, e.g., `feat(oci/objectstorage): list buckets tool`.
- PRs: description, linked issues, how-to-test, config/env notes; attach example transcripts when relevant.
- All checks must pass (`make lint test`); update examples/docs when behavior changes.

## README Format & Publishing
- Follow AWS MCP server README sections: Overview, Installation, Configuration, Tools/Resources, Usage, Development, License.
- Include a “Next: mcp-oci-servers” section linking to server packages/dirs in this repo or published Git URLs.
- Documentation uses the AWS MCP Docusaurus structure: https://github.com/awslabs/mcp/tree/main/docusaurus. Mirror section names and navigation.
- All OCI MCP servers live under `src/` (like AWS). Focus first on OCI services API tools; add Observability later.
- Use existing `dev/mcp-oci-x-services` and `dev/mcp-oci-x-server` for local development (do not create new dev servers). Production servers are created under `src/`.
- Use Context7 to download/aggregate OCI REST API docs for reference. If unavailable locally, add stubs and link to the OCI docs portal.
