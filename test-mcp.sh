#!/bin/bash

# Simple MCP Test Script
echo "=========================================="
echo "MCP-OCI Services Test"
echo "=========================================="
echo ""

# Test main service ports
echo "Testing HTTP Services (8001-8011):"
for port in $(seq 8001 8011); do
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://localhost:$port/health 2>/dev/null)
    if [ "$response" = "200" ]; then
        echo "✓ Port $port: Healthy"
    elif [ "$response" != "000" ]; then
        echo "⚠ Port $port: Responding ($response)"
    else
        echo "✗ Port $port: Not responding"
    fi
done

echo ""
echo "Testing Streamable Ports (7001-7011):"
for port in $(seq 7001 7011); do
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://localhost:$port/health 2>/dev/null)
    if [ "$response" = "200" ]; then
        echo "✓ Port $port: Healthy"
    elif [ "$response" != "000" ]; then
        echo "⚠ Port $port: Responding ($response)"
    else
        echo "✗ Port $port: Not responding"
    fi
done

echo ""
echo "Container Status:"
docker ps --filter name=mcp-oci --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -5

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="