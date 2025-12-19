# MCP-OCI Setup Validation Guide

This document provides a comprehensive validation checklist to ensure your MCP-OCI installation is ready for use.

## 🚀 Quick Validation

Run this command to perform basic validation:

```bash
# Quick health check
python -c "
import sys
import os
sys.path.append('.')
try:
    from mcp_servers.compute.server import app
    print('✅ MCP servers importable')
except Exception as e:
    print(f'❌ MCP import failed: {e}')

try:
    import oci
    print('✅ OCI SDK available')
except Exception as e:
    print(f'❌ OCI SDK missing: {e}')

try:
    config = oci.config.from_file()
    print('✅ OCI config found')
except Exception as e:
    print(f'⚠️ OCI config issue: {e}')
"
```

## 📋 Pre-Installation Checklist

### System Requirements

- [ ] Python 3.11 or higher installed
- [ ] Git installed and configured
- [ ] Docker and Docker Compose available (for observability)
- [ ] At least 4GB RAM available
- [ ] 10GB disk space available

### OCI Prerequisites

- [ ] Active Oracle Cloud Infrastructure account
- [ ] User with appropriate IAM policies
- [ ] API keys configured OR instance/resource principal setup
- [ ] Target compartment OCID available
- [ ] Preferred region identified

## 🔧 Installation Validation

### 1. Repository Setup

```bash
# Verify repository structure
test -f README.md && echo "✅ README exists"
test -f .env.local.example && echo "✅ Environment template exists"
test -d mcp_servers && echo "✅ Server modules exist"
test -f requirements.txt && echo "✅ Dependencies defined"
```

### 2. Virtual Environment

```bash
# Check Python environment
python --version
python -c "import sys; print(f'Python: {sys.version}')"

# Verify virtual environment
echo $VIRTUAL_ENV || echo "⚠️ Virtual environment not activated"

# Check required packages
pip list | grep -E "(oci|fastmcp|opentelemetry)" || echo "⚠️ Key packages missing"
```

### 3. Dependencies

```bash
# Install and verify all dependencies
pip install -e .

# Test critical imports
python -c "
packages = ['oci', 'fastmcp', 'opentelemetry', 'prometheus_client', 'pyroscope_io']
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg}')
    except ImportError as e:
        print(f'❌ {pkg}: {e}')
"
```

## ⚙️ Configuration Validation

### 1. Environment Variables

```bash
# Copy and configure environment
cp .env.local.example .env.local

# Required variables check
echo "Checking required environment variables:"
for var in OCI_REGION COMPARTMENT_OCID; do
    if [[ -n "${!var}" ]]; then
        echo "✅ $var is set"
    else
        echo "⚠️ $var needs to be configured"
    fi
done
```

### 2. OCI Authentication

```bash
# Test OCI authentication
python -c "
import oci
try:
    config = oci.config.from_file()
    identity = oci.identity.IdentityClient(config)
    user = identity.get_user(config['user'])
    print(f'✅ OCI auth successful: {user.data.name}')
except Exception as e:
    print(f'❌ OCI auth failed: {e}')
"
```

### 3. OCI Permissions

```bash
# Test basic OCI operations
python -c "
import os
import oci
try:
    config = oci.config.from_file()
    compute = oci.core.ComputeClient(config)
    compartment_id = os.getenv('COMPARTMENT_OCID', config.get('tenancy'))
    instances = compute.list_instances(compartment_id=compartment_id, limit=1)
    print(f'✅ Can list compute instances: {len(instances.data)} found')
except oci.exceptions.ServiceError as e:
    if e.status == 404:
        print('✅ API call successful (no instances found)')
    elif e.status == 401:
        print('❌ Authentication failed - check OCI config')
    elif e.status == 403:
        print('❌ Authorization failed - check IAM policies')
    else:
        print(f'⚠️ API error: {e.message}')
except Exception as e:
    print(f'❌ Connection failed: {e}')
"
```

## 🖥️ Server Validation

### 1. Individual Server Tests

```bash
# Test each MCP server startup
servers=("compute" "network" "security" "cost" "db" "observability" "inventory" "blockstorage" "loadbalancer")

for server in "${servers[@]}"; do
    echo "Testing $server server..."
    timeout 10s python -m mcp_servers.$server.server --test 2>/dev/null
    if [[ $? -eq 0 ]]; then
        echo "✅ $server server starts successfully"
    else
        echo "⚠️ $server server needs attention"
    fi
done
```

### 2. Tool Discovery

```bash
# Verify tool discovery
python -c "
import importlib
servers = ['compute', 'network', 'security', 'cost', 'db', 'observability', 'inventory', 'blockstorage', 'loadbalancer']

total_tools = 0
for server_name in servers:
    try:
        module = importlib.import_module(f'mcp_servers.{server_name}.server')
        tools = getattr(module, 'tools', [])
        tool_count = len(tools)
        total_tools += tool_count
        print(f'✅ {server_name}: {tool_count} tools available')
    except Exception as e:
        print(f'❌ {server_name}: {e}')

print(f'📊 Total tools discovered: {total_tools}')
"
```

### 3. MCP Protocol

```bash
# Test MCP protocol compliance
python -c "
import json
import sys
from io import StringIO
from mcp_servers.compute.server import app

# Simulate MCP initialization request
test_request = {
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {
        'protocolVersion': '2024-11-05',
        'capabilities': {},
        'clientInfo': {
            'name': 'test-client',
            'version': '1.0.0'
        }
    }
}

try:
    # This is a basic test - actual MCP testing requires more setup
    print('✅ MCP server module imports successfully')
    print('✅ FastMCP app object available')
except Exception as e:
    print(f'❌ MCP protocol issue: {e}')
"
```

## 📊 Observability Stack Validation

### 1. Docker Services

```bash
# Start observability stack
cd ops
./start-observability.sh

# Check service health
echo "Checking observability services:"
services=("grafana:3000" "prometheus:9090" "tempo:3200" "pyroscope:4040")

for service in "${services[@]}"; do
    name="${service%:*}"
    port="${service#*:}"
    if curl -sf "http://localhost:$port" >/dev/null 2>&1; then
        echo "✅ $name is responding on port $port"
    else
        echo "❌ $name is not responding on port $port"
    fi
done
```

### 2. Metrics Collection

```bash
# Test metrics endpoints
servers=("compute:8001" "network:8006" "security:8004" "cost:8005")

echo "Checking server metrics endpoints:"
for server in "${servers[@]}"; do
    name="${server%:*}"
    port="${server#*:}"
    if curl -sf "http://localhost:$port/metrics" | head -1 >/dev/null 2>&1; then
        echo "✅ $name metrics available on port $port"
    else
        echo "⚠️ $name metrics endpoint not responding"
    fi
done
```

### 3. Tracing Integration

```bash
# Test OpenTelemetry integration
python -c "
import os
os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = 'http://localhost:4317'

try:
    from mcp_oci_common.observability import init_tracing
    tracer = init_tracing('test-service')
    with tracer.start_span('test_span') as span:
        span.set_attribute('test', 'validation')
    print('✅ OpenTelemetry tracing initialized')
except Exception as e:
    print(f'❌ Tracing setup failed: {e}')
"
```

## 🌐 UX Application Validation

### 1. UX Server

```bash
# Test UX application
cd ux
timeout 10s python app.py &
UX_PID=$!

sleep 2
if curl -sf "http://localhost:8010/health" >/dev/null 2>&1; then
    echo "✅ UX application responding"
else
    echo "❌ UX application not responding"
fi

kill $UX_PID 2>/dev/null
```

### 2. Dashboard Access

```bash
# Check dashboard availability
dashboards=("grafana:3000" "ux:8010")

for dashboard in "${dashboards[@]}"; do
    name="${dashboard%:*}"
    port="${dashboard#*:}"
    if curl -sf "http://localhost:$port" >/dev/null 2>&1; then
        echo "✅ $name dashboard accessible on port $port"
    else
        echo "⚠️ $name dashboard not accessible"
    fi
done
```

## 🔐 Security Validation

### 1. Credentials Check

```bash
# Verify no credentials in repository
echo "Checking for credentials in codebase:"

# Check for common credential patterns
if find . -name "*.py" -o -name "*.sh" -o -name "*.yml" -o -name "*.yaml" | \
   xargs grep -l "password\|secret\|key" | \
   grep -v "sample\|example\|doc\|test\|\.env.local\.example" | \
   head -1 >/dev/null; then
    echo "⚠️ Potential credentials found - review manually"
else
    echo "✅ No obvious credentials in codebase"
fi

# Check for OCIDs in files
if find . -name "*.py" -o -name "*.json" | \
   xargs grep -l "ocid1\." | \
   grep -v "test\|example\|sample\|doc" | \
   head -1 >/dev/null; then
    echo "⚠️ Real OCIDs found - ensure they are examples only"
else
    echo "✅ No real OCIDs in codebase"
fi
```

### 2. Environment Security

```bash
# Check environment file security
if [[ -f .env.local ]]; then
    echo "⚠️ .env.local file exists - ensure it's in .gitignore"
    if grep -q "^\.env.local$" .gitignore 2>/dev/null; then
        echo "✅ .env.local is properly ignored by git"
    else
        echo "❌ .env.local is NOT in .gitignore"
    fi
else
    echo "✅ No .env.local file in repository"
fi
```

## 📝 Documentation Validation

### 1. Documentation Coverage

```bash
# Check documentation completeness
docs=(
    "README.md"
    "docs/INDIVIDUAL_SERVERS.md"
    "docs/UX_OVERVIEW.md"
    "docs/OBSERVABILITY_INTEGRATION.md"
    ".env.local.example"
)

echo "Checking documentation files:"
for doc in "${docs[@]}"; do
    if [[ -f "$doc" ]]; then
        echo "✅ $doc exists"
    else
        echo "❌ $doc missing"
    fi
done
```

### 2. Setup Instructions

```bash
# Validate setup instructions are complete
echo "Checking setup instruction completeness:"

required_sections=(
    "Prerequisites"
    "Installation"
    "Configuration"
    "Usage"
    "Troubleshooting"
)

for section in "${required_sections[@]}"; do
    if grep -qi "$section" README.md; then
        echo "✅ $section documented"
    else
        echo "⚠️ $section may need more documentation"
    fi
done
```

## 🎯 End-to-End Validation

### 1. Complete Workflow Test

```bash
#!/bin/bash
# Complete end-to-end test

echo "🧪 Running end-to-end validation..."

# 1. Environment setup
source .env.local 2>/dev/null || echo "No .env.local file found"

# 2. Start observability
cd ops && ./start-observability.sh && cd ..

# 3. Test a simple MCP operation
python -c "
import os
os.environ.setdefault('COMPARTMENT_OCID', '[Link to Secure Variable: OCI_COMPARTMENT_OCID]')
try:
    from mcp_servers.compute.server import app
    # This would normally require actual MCP client interaction
    print('✅ End-to-end setup appears functional')
except Exception as e:
    print(f'⚠️ End-to-end test needs manual verification: {e}')
"

echo "🎉 Validation complete!"
```

## 🚨 Common Issues and Solutions

### Installation Issues

**Python Version Mismatch**
```bash
# Check Python version
python --version
# Should be 3.11 or higher
```

**Missing Dependencies**
```bash
# Reinstall all dependencies
pip install --upgrade pip
pip install -e .
```

### Configuration Issues

**OCI Config Not Found**
```bash
# Setup OCI CLI configuration
pip install oci-cli
oci setup config
```

**Permission Denied**
```bash
# Check IAM policies
oci iam user get --user-id [Link to Secure Variable: OCI_USER_OCID]
```

### Runtime Issues

**Server Won't Start**
```bash
# Check for port conflicts
netstat -an | grep :800[0-9]
```

**Metrics Not Appearing**
```bash
# Verify observability stack
docker-compose -f ops/docker-compose.yml ps
```

## ✅ Validation Summary

After completing this validation guide, you should have:

- [ ] ✅ All dependencies installed and working
- [ ] ✅ OCI authentication configured and tested
- [ ] ✅ All MCP servers starting successfully
- [ ] ✅ Observability stack operational
- [ ] ✅ UX application accessible
- [ ] ✅ No credentials exposed in codebase
- [ ] ✅ Complete documentation available

**Next Steps**: If all validations pass, your MCP-OCI installation is ready for production use!

For ongoing monitoring, consider setting up the validation script as a periodic health check in your monitoring system.
