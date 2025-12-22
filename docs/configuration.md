# Configuration Guide

MCP-OCI supports flexible configuration through environment variables, with automatic loading from `.env.local` files.

## Configuration Priority

Configuration is loaded in the following order (later sources override earlier ones):

1. **`.env.local`** (highest priority, git-ignored)
2. **Environment variables** (OCI Vault injection or system environment)
3. **Default values** (hardcoded in code)

## Quick Start

1. **Copy the example file**:
   ```bash
   cp .env.local.example .env.local
   ```

2. **Edit `.env.local`** with your values:
   ```bash
   # Required: OCI Configuration
   OCI_PROFILE=DEFAULT
   OCI_REGION=us-ashburn-1
   
   # OCI APM (Production)
   OCI_APM_ENDPOINT=[Link to Secure Variable: OCI_APM_ENDPOINT]
   OCI_APM_PRIVATE_DATA_KEY=[Link to Secure Variable: OCI_APM_PRIVATE_DATA_KEY]
   OTEL_DISABLE_LOCAL=true
   ```

3. **Start servers** - `.env.local` is automatically loaded:
   ```bash
   ./scripts/install.sh
   # or
   scripts/mcp-launchers/start-mcp-server.sh all --daemon
   ```

## Configuration Files

### `.env.local` (Recommended)

This file is:
- **Git-ignored** (safe for secrets)
- **Automatically loaded** by all scripts and Python modules
- **Highest priority** (overrides all other sources)

Location: Project root (`mcp-oci/.env.local`)

### `.env.local.example` (Template)

Example file for documentation and onboarding. Copy to `.env.local` and fill in values.

## Environment Variables

### OCI Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OCI_PROFILE` | OCI CLI profile name | No | `DEFAULT` |
| `OCI_REGION` | Target OCI region | No | `us-ashburn-1` |
| `COMPARTMENT_OCID` | Default compartment OCID | No | Tenancy OCID |
| `TENANCY_OCID` | Tenancy OCID | No | From OCI config |

### OCI APM Telemetry

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OCI_APM_ENDPOINT` | OCI APM OTLP endpoint URL | Yes (for APM) | - |
| `OCI_APM_PRIVATE_DATA_KEY` | Private data key for APM | Yes (for APM) | - |
| `OTEL_DISABLE_LOCAL` | Disable local OTEL collector | No | `false` |

### OpenTelemetry (Local Collector)

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint | No | `localhost:4317` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | Protocol (grpc/http) | No | `grpc` |
| `OTEL_SERVICE_NAME` | Service name | No | Auto-detected |
| `OTEL_SERVICE_NAMESPACE` | Service namespace | No | `mcp-oci` |
| `DEPLOYMENT_ENVIRONMENT` | Environment tag | No | `local` |

### MCP Server Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ALLOW_MUTATIONS` | Enable write operations | No | `false` |
| `MCP_OCI_PRIVACY` | Mask OCIDs in responses | No | `true` |
| `MCP_CACHE_DIR` | Shared cache directory | No | `~/.mcp-oci/cache` |
| `MCP_CACHE_BACKEND` | Cache backend (`file` or `redis`) | No | `file` |
| `MCP_REDIS_URL` | Redis connection URL for shared cache | No | `redis://localhost:6379` |
| `MCP_CACHE_KEY_PREFIX` | Redis key prefix for shared cache | No | `mcp:cache` |

### Server Ports

| Variable | Description | Default |
|----------|-------------|---------|
| `METRICS_PORT` | Prometheus metrics port | Server-specific |
| `MCP_PORT_COMPUTE` | Compute server port | `7001` |
| `MCP_PORT_DB` | Database server port | `7002` |
| `MCP_PORT_NETWORK` | Network server port | `7006` |
| `MCP_PORT_SECURITY` | Security server port | `7004` |
| `MCP_PORT_COST` | Cost server port | `7005` |
| `MCP_PORT_OBSERVABILITY` | Observability server port | `7003` |
| `MCP_PORT_BLOCKSTORAGE` | Block storage server port | `7007` |
| `MCP_PORT_LOADBALANCER` | Load balancer server port | `7008` |
| `MCP_PORT_INVENTORY` | Inventory server port | `7009` |
| `MCP_PORT_AGENTS` | Agents server port | `7011` |

## Automatic Loading

All scripts and Python modules automatically load `.env.local`:

- **Python modules**: Load via `dotenv` at import time
- **Shell scripts**: Source `.env.local` before execution
- **Docker Compose**: Uses `env_file: .env.local`

## Examples

### Production Configuration (OCI APM)

```bash
# .env.local
OCI_PROFILE=PRODUCTION
OCI_REGION=eu-frankfurt-1
OCI_APM_ENDPOINT=[Link to Secure Variable: OCI_APM_ENDPOINT]
OCI_APM_PRIVATE_DATA_KEY=[Link to Secure Variable: OCI_APM_PRIVATE_DATA_KEY]
OTEL_DISABLE_LOCAL=true
ALLOW_MUTATIONS=false
MCP_OCI_PRIVACY=true
```

### Development Configuration (Local Collector)

```bash
# .env.local
OCI_PROFILE=DEFAULT
OCI_REGION=us-ashburn-1
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
ALLOW_MUTATIONS=true
MCP_OCI_PRIVACY=false
DEBUG=true
```

### Multi-Environment Setup

You can use different `.env.local` files for different environments:

```bash
# Development
cp .env.local.example .env.local
# Edit for development

# Production (OCI Vault)
# Inject required variables from OCI Vault at runtime.
```

## Security Best Practices

1. **Never commit `.env.local`** - It's already in `.gitignore`
2. **Use `.env.local.example`** - Commit example files without secrets
3. **Rotate keys regularly** - Especially `OCI_APM_PRIVATE_DATA_KEY`
4. **Use least privilege** - Set `ALLOW_MUTATIONS=false` in production
5. **Enable privacy** - Keep `MCP_OCI_PRIVACY=true` in production
6. **Keep `.venv311` consistent** - The installer now mirrors your local `.venv` to `.venv311` so stdio servers always have a reproducible Python path.

## Troubleshooting

### Variables Not Loading

1. **Check file location**: `.env.local` must be in project root
2. **Check file permissions**: Ensure file is readable
3. **Check syntax**: No spaces around `=` in variable assignments
4. **Check quotes**: Use quotes for values with spaces

### Variables Overridden

Remember the priority order:
- `.env.local` > Environment > Defaults

If a variable is set in multiple places, `.env.local` wins.

### Python Modules Not Loading

Python modules load `.env.local` automatically via `dotenv`. If it's not working:
1. Ensure `python-dotenv` is installed: `pip install python-dotenv`
2. Check that the file is in the project root
3. Verify the file is readable

## Related Documentation

- [Telemetry Configuration](telemetry.md)
- [Tenancy Discovery](tenancy-discovery.md)
- [Installation Guide](../README.md#installation)
