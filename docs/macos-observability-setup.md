# macOS Observability Setup with Colima

This guide explains how to set up and run the complete MCP-OCI observability stack on macOS using Colima (a Docker Desktop alternative).

## Prerequisites

- **macOS** (10.15 or later)
- **Homebrew** (install from [brew.sh](https://brew.sh/))
- **Colima** (automatically installed by the script if missing)
- **Docker** (automatically configured with Colima)

## Quick Start

1. **Navigate to the scripts directory:**
   ```bash
   cd /Users/abirzu/dev/mcp-oci/scripts
   ```

2. **Run the observability stack:**
   ```bash
   ./start-observability-macos.sh start
   ```

That's it! The script will:
- ✅ Check and install requirements
- ✅ Start Colima with appropriate resources
- ✅ Launch all observability services
- ✅ Show access URLs

## Available Commands

```bash
# Start the observability stack (default)
./start-observability-macos.sh start

# Check status of services
./start-observability-macos.sh status

# Stop all services
./start-observability-macos.sh stop

# Restart services
./start-observability-macos.sh restart

# Complete cleanup (stops services and Colima)
./start-observability-macos.sh cleanup
```

## Services Included

The script starts a complete observability stack:

| Service | URL | Purpose |
|---------|-----|---------|
| **Grafana** | http://localhost:3000 | Dashboards & Visualization |
| **Prometheus** | http://localhost:9090 | Metrics Collection |
| **Tempo** | http://localhost:3200 | Distributed Tracing |
| **Pyroscope** | http://localhost:4040 | Continuous Profiling |
| **OTLP Collector** | http://localhost:4317 | Data Ingestion |
| **Observability App** | http://localhost:8000 | MCP Observability Service |

## Grafana Access

- **URL**: http://localhost:3000
- **Username**: `admin`
- **Password**: `admin`

### Pre-configured Dashboards

- **MCP Monitoring Dashboard** (auto-provisioned)
- Default Grafana system dashboards

## Colima Configuration

The script creates a dedicated Colima profile called `mcp-oci-observability` with:

- **CPU**: 2 cores
- **Memory**: 4GB
- **Disk**: 10GB
- **Network**: Host accessible
- **File System**: VirtioFS for performance

## Troubleshooting

### Services Not Starting

1. **Check Colima status:**
   ```bash
   colima status mcp-oci-observability
   ```

2. **View service logs:**
   ```bash
   cd /Users/abirzu/dev/mcp-oci/ops
   docker-compose logs -f [service-name]
   ```

3. **Restart Colima:**
   ```bash
   colima stop mcp-oci-observability
   colima start mcp-oci-observability
   ```

### Port Conflicts

If ports 3000, 9090, etc. are already in use:

1. **Check what's using the ports:**
   ```bash
   lsof -i :3000
   ```

2. **Stop conflicting services or change ports in `docker-compose.yml`**

### Permission Issues

If you get permission errors:

```bash
# Fix Colima permissions
sudo chown -R $(whoami) ~/.colima
```

## Manual Control

You can also control services manually:

```bash
# Go to the ops directory
cd /Users/abirzu/dev/mcp-oci/ops

# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f grafana
```

## Resource Usage

The observability stack requires approximately:
- **CPU**: 1-2 cores
- **Memory**: 2-4GB RAM
- **Disk**: 2-5GB storage

Monitor resource usage with:
```bash
colima status mcp-oci-observability
docker stats
```

## Data Persistence

- **Grafana dashboards**: Persisted in `./ops/grafana/dashboards/`
- **Prometheus data**: Ephemeral (restarts with clean state)
- **Tempo traces**: Ephemeral
- **Pyroscope profiles**: Persisted in `./ops/pyroscope/`

## Integration with MCP Servers

The observability services are automatically configured to receive data from the MCP-OCI servers. All MCP servers send:

- **Metrics** → Prometheus (via OTLP)
- **Traces** → Tempo (via OTLP)
- **Logs** → Tempo (via OTLP)
- **Profiles** → Pyroscope (optional)

## Environment Variables

Customize behavior with environment variables:

```bash
# Enable Pyroscope profiling in MCP servers
export ENABLE_PYROSCOPE=true

# Set custom OTLP endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Configure metrics ports
export METRICS_PORT=8001  # For individual MCP servers
```

## Next Steps

1. **Access Grafana** at http://localhost:3000
2. **Import dashboards** from `./ops/grafana/dashboards/`
3. **Configure data sources** (Prometheus, Tempo, Pyroscope)
4. **Start sending telemetry** from your applications

## Support

If you encounter issues:

1. Check the [troubleshooting documentation](../docs/troubleshooting.md)
2. View service logs: `docker-compose logs -f`
3. Restart with cleanup: `./start-observability-macos.sh cleanup && ./start-observability-macos.sh start`
