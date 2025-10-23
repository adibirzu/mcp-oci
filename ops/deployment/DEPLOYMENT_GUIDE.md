# MCP-OCI Server Deployment Guide

## Overview
This guide provides comprehensive instructions for deploying MCP-OCI servers in various environments with multiple connection options.

## Deployment Options

### 1. Local Development
- Docker Compose deployment
- Direct Python execution
- Development mode with hot reload

### 2. Cloud Deployment
- OCI Compute Instance (Terraform)
- OCI Container Instance
- Kubernetes (OKE)
- Docker Swarm

### 3. Hybrid Deployment
- Local + Cloud failover
- Multi-region deployment
- Load-balanced configurations

## Connection Methods

### 1. HTTP/HTTPS (Streamable)
- Port range: 7001-7011, 8000-8011
- Protocol: HTTP with SSE (Server-Sent Events)
- Use case: Web clients, Claude Desktop

### 2. WebSocket
- Port: 9000
- Protocol: WebSocket
- Use case: Real-time bidirectional communication

### 3. gRPC
- Port: 50051
- Protocol: gRPC/HTTP2
- Use case: High-performance service-to-service

### 4. Unix Socket (Local only)
- Path: /tmp/mcp-oci.sock
- Protocol: Unix domain socket
- Use case: Local inter-process communication

## Prerequisites

### System Requirements
- Python 3.11+
- Docker 24.0+
- OCI CLI configured
- Terraform 1.5+
- 2GB+ RAM
- 10GB+ disk space

### OCI Requirements
- Valid OCI account
- Compartment with appropriate permissions
- Network configuration (VCN, Subnet)
- SSH key pair

## Quick Start

### Local Deployment
```bash
cd /Users/abirzu/dev/mcp-oci
./scripts/deploy/local-deploy.sh
```

### Cloud Deployment
```bash
cd /Users/abirzu/dev/mcp-oci
./scripts/deploy/cloud-deploy.sh
```

### Hybrid Deployment
```bash
cd /Users/abirzu/dev/mcp-oci
./scripts/deploy/hybrid-deploy.sh
```

## Configuration Files

### Environment Variables
- `.env.local` - Local development
- `.env.cloud` - Cloud deployment
- `.env.production` - Production settings

### Connection Configurations
- `configs/connections/local.json`
- `configs/connections/cloud.json`
- `configs/connections/hybrid.json`

## Monitoring & Health Checks

### Health Check Endpoints
- HTTP: `http://localhost:8000/health`
- WebSocket: `ws://localhost:9000/health`
- gRPC: `localhost:50051/health`

### Monitoring Tools
- Prometheus metrics: `/metrics`
- OpenTelemetry tracing
- Custom dashboards

## Troubleshooting

### Common Issues
1. Port conflicts
2. Authentication failures
3. Network connectivity
4. Resource limits

### Debug Commands
```bash
# Check server status
./scripts/deploy/check-status.sh

# View logs
./scripts/deploy/view-logs.sh

# Test connections
./scripts/deploy/test-connections.sh
```

## Security Considerations

### Authentication Methods
- API Key
- OAuth2
- Instance Principal (OCI)
- mTLS

### Network Security
- Firewall rules
- Network Security Groups
- SSL/TLS encryption
- IP whitelisting

## Performance Tuning

### Resource Allocation
- CPU: 2-4 cores recommended
- Memory: 2-8GB depending on load
- Network: 1Gbps+ for production

### Scaling Options
- Horizontal scaling with load balancer
- Vertical scaling for single instance
- Auto-scaling based on metrics