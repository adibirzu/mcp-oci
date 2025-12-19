# MCP-OCI Server Deployment System

## Quick Start

### Local Development
```bash
# Quick local deployment with Docker
./scripts/deploy/local-deploy.sh docker streamable

# Local deployment with Python
./scripts/deploy/local-deploy.sh python all

# Check health status
./scripts/deploy/health-check.sh all localhost
```

### Cloud Deployment
```bash
# Deploy to OCI Compute Instance
./scripts/deploy/cloud-deploy.sh compute eu-frankfurt-1 <compartment_id>

# Deploy to Kubernetes (OKE)
./scripts/deploy/cloud-deploy.sh kubernetes eu-frankfurt-1 <compartment_id>

# Test cloud deployment
./scripts/deploy/test-connections.sh <public_ip> full
```

## Deployment Options

### 1. Local Development

#### Docker Compose (Recommended)
```bash
# Start all services
docker-compose up -d

# Start with specific profile
docker-compose --profile monitoring up -d

# View logs
docker-compose logs -f mcp-oci

# Stop services
docker-compose down
```

#### Direct Python
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start servers
python -m mcp_servers.orchestrator
```

#### Claude Desktop Integration
```bash
# Copy configuration to Claude Desktop
cp configs/claude-desktop-config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Restart Claude Desktop
```

### 2. Cloud Deployment

#### OCI Compute Instance
The cloud deployment was already set up via Terraform:
- Instance IP: <PUBLIC_IP>
- Shape: VM.Standard.E4.Flex (2 OCPU, 32GB RAM)
- Region: eu-frankfurt-1

Access the instance:
```bash
ssh -i ~/.ssh/id_rsa opc@<PUBLIC_IP>
```

#### Container Instance
```bash
# Build and push image to OCIR
docker build -t mcp-oci:latest .
docker tag mcp-oci:latest <region>.ocir.io/<namespace>/mcp-oci:latest
docker push <region>.ocir.io/<namespace>/mcp-oci:latest

# Deploy
./scripts/deploy/cloud-deploy.sh container eu-frankfurt-1
```

#### Kubernetes (OKE)
```bash
# Ensure kubectl is configured
oci ce cluster create-kubeconfig --cluster-id <cluster_id>

# Deploy to Kubernetes
./scripts/deploy/cloud-deploy.sh kubernetes eu-frankfurt-1
```

## Connection Methods

### HTTP/SSE (Streamable)
Primary connection method for Claude Desktop and web clients.

**Endpoints:**
- Compute: `http://localhost:7001`
- Database: `http://localhost:7002`
- Network: `http://localhost:7003`
- Cost: `http://localhost:7007`
- Main Orchestrator: `http://localhost:8000`

**Example:**
```bash
# Health check
curl http://localhost:8000/health

# List instances
curl -X POST http://localhost:7001/tools/list_instances \
  -H "Content-Type: application/json" \
  -d '{"compartment_id": "[Link to Secure Variable: OCI_COMPARTMENT_OCID]"}'
```

### WebSocket
Real-time bidirectional communication.

**Endpoint:** `ws://localhost:9000`

**Example (Python):**
```python
import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:9000") as ws:
        await ws.send(json.dumps({"action": "list_instances"}))
        response = await ws.recv()
        print(json.loads(response))

asyncio.run(test())
```

### gRPC
High-performance service-to-service communication.

**Endpoint:** `localhost:50051`

**Example:**
```bash
# List services
grpcurl -plaintext localhost:50051 list

# Call method
grpcurl -plaintext -d '{"compartment_id": "..."}' \
  localhost:50051 mcp.oci.compute/ListInstances
```

## Configuration Files

### Environment Variables (`.env.local`)
```bash
# OCI Configuration
OCI_CLI_AUTH=api_key
OCI_CONFIG_FILE=~/.oci/config
OCI_CONFIG_PROFILE=DEFAULT
COMPARTMENT_ID=[Link to Secure Variable: OCI_COMPARTMENT_OCID]

# MCP Settings
MCP_TRANSPORT=streamable
MCP_HOST=0.0.0.0
MCP_ENV=production
MCP_LOG_LEVEL=INFO

# Performance
MCP_WORKER_COUNT=4
MCP_TIMEOUT=30
MCP_MAX_CONNECTIONS=1000
```

### Connection Configurations
- `configs/connections/local.json` - Local development settings
- `configs/connections/cloud.json` - Cloud production settings
- `configs/claude-desktop-config.json` - Claude Desktop integration

## Health Monitoring

### Health Check Script
```bash
# Full health check
./scripts/deploy/health-check.sh all localhost

# Specific checks
./scripts/deploy/health-check.sh http localhost
./scripts/deploy/health-check.sh websocket <PUBLIC_IP>
./scripts/deploy/health-check.sh metrics localhost
```

### Metrics Endpoint
Access Prometheus metrics at `http://localhost:9090/metrics`

### Monitoring Stack (Optional)
```bash
# Start monitoring stack
docker-compose --profile monitoring up -d

# Access services
# - Prometheus: http://localhost:9091
# - Grafana: http://localhost:3000 (admin/admin)
```

## Testing

### Quick Test
```bash
./scripts/deploy/test-connections.sh localhost quick
```

### Full Test Suite
```bash
./scripts/deploy/test-connections.sh localhost full
```

### Stress Testing
```bash
./scripts/deploy/test-connections.sh localhost stress
```

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port
lsof -i :7001

# Kill process
kill -9 <PID>
```

#### Docker Container Not Starting
```bash
# Check logs
docker logs mcp-oci-main

# Rebuild image
docker-compose build --no-cache
```

#### OCI Authentication Issues
```bash
# Verify OCI CLI configuration
oci iam user get --user-id <your-user-id>

# Test with instance principal (on OCI instance)
export OCI_CLI_AUTH=instance_principal
oci iam compartment list
```

#### Connection Refused
```bash
# Check if service is running
docker ps | grep mcp-oci

# Check firewall/security groups
sudo firewall-cmd --list-all
```

### Debug Mode
```bash
# Enable debug logging
export MCP_LOG_LEVEL=DEBUG
export MCP_DEBUG=true

# Run with verbose output
./scripts/deploy/local-deploy.sh docker all 2>&1 | tee debug.log
```

## Security Considerations

### Production Deployment
1. **Never expose ports directly to internet without authentication**
2. **Use HTTPS/WSS in production**
3. **Implement rate limiting**
4. **Enable firewall rules**
5. **Use instance principal authentication on OCI**

### SSL/TLS Configuration
```bash
# Generate self-signed certificate (for testing)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Configure nginx proxy
docker-compose --profile proxy up -d
```

### Access Control
```bash
# Restrict access by IP (OCI Security List)
oci network security-list update \
  --security-list-id <security-list-id> \
  --ingress-security-rules '[{"source": "203.0.113.0/24", "protocol": "6", "tcpOptions": {"destinationPortRange": {"min": 7001, "max": 7011}}}]'
```

## Performance Tuning

### Docker Resources
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
```

### Connection Pool
```bash
export MCP_MAX_CONNECTIONS=1000
export MCP_WORKER_COUNT=8
```

### Caching (Redis)
```bash
# Enable Redis caching
docker-compose --profile cache up -d

# Configure in .env.local
export MCP_CACHE_ENABLED=true
export MCP_CACHE_REDIS_URL=redis://localhost:6379
```

## Maintenance

### Backup Configuration
```bash
# Backup configs
tar -czf mcp-configs-$(date +%Y%m%d).tar.gz configs/

# Backup logs
tar -czf mcp-logs-$(date +%Y%m%d).tar.gz logs/
```

### Update Deployment
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Log Rotation
```bash
# Setup logrotate (Linux)
cat > /etc/logrotate.d/mcp-oci <<EOF
/path/to/mcp-oci/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

## Support

For issues or questions:
1. Check logs: `docker logs mcp-oci-main`
2. Run health check: `./scripts/deploy/health-check.sh`
3. Review documentation: `docs/`
4. Open an issue on GitHub
