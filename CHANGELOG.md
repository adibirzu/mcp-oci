# Changelog

All notable changes to MCP-OCI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **OCI APM Configuration**: Updated all configuration files and documentation to use the configured OCI APM endpoint (eu-frankfurt-1)
- **Environment Variables**: All variables now automatically load from `.env.local` with OCI APM pre-configured
- **Server Launcher**: Automatically disables local OTEL collector when OCI APM is configured

### Added
- **Tenancy Discovery**: Automatic tenancy discovery at server startup
  - New `scripts/init_tenancy_discovery.py` script for discovering tenancy information
  - Automatic discovery runs during installation and server startup
  - Cache stored at `~/.mcp-oci/cache/tenancy_discovery.json`
  - See [Tenancy Discovery Guide](docs/tenancy-discovery.md) for details

- **OCI APM Telemetry Support**: Enhanced telemetry configuration
  - Priority-based telemetry configuration (OCI APM > Explicit Endpoint > Local Collector)
  - Automatic OCI APM configuration when `OCI_APM_ENDPOINT` and `OCI_APM_PRIVATE_DATA_KEY` are set
  - Option to disable local OTEL collector with `OTEL_DISABLE_LOCAL=true`
  - See [Telemetry Configuration Guide](docs/telemetry.md) for details

- **Enhanced Compute Server**: Comprehensive instance information
  - Instance listing now includes boot volumes and block volumes
  - New `get_instance_cost` tool for cost breakdown including volumes
  - New `get_comprehensive_instance_details` tool for all instance information
  - See [Compute Instance Optimization](docs/compute-instance-optimization.md) for details

### Changed
- **Installation Scripts**: Updated to run tenancy discovery before starting servers
- **OTEL Configuration**: OCI APM now takes precedence over local collector
- **Server Launcher**: Automatically runs tenancy discovery before starting servers

### Documentation
- Added [Telemetry Configuration Guide](docs/telemetry.md)
- Added [Tenancy Discovery Guide](docs/tenancy-discovery.md)
- Added [Compute Instance Optimization Guide](docs/compute-instance-optimization.md)
- Updated README with telemetry and tenancy discovery information

## [2.0.0] - 2024-01-15

### Added
- Multi-domain MCP server suite
- FastMCP integration
- OpenTelemetry observability
- Privacy-aware responses
- Docker deployment support

### Changed
- Migrated from legacy FastMCP implementation
- Unified server architecture

## [1.0.0] - 2023-12-01

### Added
- Initial release
- Basic MCP server implementations
- OCI SDK integration
