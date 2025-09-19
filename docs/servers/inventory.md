# OCI Inventory MCP Server

Provides tools for OCI resource inventory and reporting.

## Available Tools

### run_showoci
Run ShowOCI inventory report with optional diff for changes.
- Parameters:
  - profile: OCI config profile
  - regions: List of regions
  - compartments: List of compartment OCIDs
  - resource_types: List of resource types to include
  - output_format: text or csv (default: text)
  - diff_mode: Enable diff from previous run (default: true)
  - limit: Limit output lines

### run_showoci_simple
Convenience wrapper accepting comma-separated strings.
- Parameters: Same as run_showoci but strings instead of lists

### generate_compute_capacity_report
Generate compute capacity report with utilization, IPs, and recommendations.
- Parameters:
  - compartment_id: Target compartment
  - region: OCI region
  - profile: OCI config profile
  - include_metrics: Include utilization metrics (default: true)
  - output_format: json or summary (default: json)
