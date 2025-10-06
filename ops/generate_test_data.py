#!/usr/bin/env python3
"""
Generate test data for the observability stack
"""

import time
import random
import requests
import json
import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

def generate_prometheus_metrics():
    """Generate test metrics that can be scraped by Prometheus"""
    from prometheus_client import Counter, Histogram, start_http_server, REGISTRY
    from prometheus_client.core import CollectorRegistry

    # Clear existing metrics
    for collector in list(REGISTRY._collector_to_names.keys()):
        try:
            REGISTRY.unregister(collector)
        except:
            pass

    # Create test metrics
    tool_calls = Counter(
        'mcp_tool_calls_total',
        'Total MCP tool calls',
        ['server', 'tool', 'outcome']
    )

    tool_duration = Histogram(
        'mcp_tool_duration_seconds',
        'MCP tool duration in seconds',
        ['server', 'tool']
    )

    oci_tokens = Counter(
        'oci_mcp_tokens_total',
        'Total OCI MCP tokens used',
        ['service', 'operation']
    )

    print("🚀 Starting metrics generator on port 8012...")
    start_http_server(8012)

    # Generate test data
    servers = ['mcp-compute', 'mcp-network', 'mcp-security', 'mcp-observability']
    tools = ['list_instances', 'get_metrics', 'scan_vulnerabilities', 'analyze_traces']

    print("📊 Generating test metrics...")

    try:
        while True:
            # Generate tool calls
            server = random.choice(servers)
            tool = random.choice(tools)
            outcome = random.choice(['success', 'success', 'success', 'error'])  # 75% success rate

            tool_calls.labels(server=server, tool=tool, outcome=outcome).inc()

            # Generate tool duration
            duration = random.uniform(0.1, 5.0)  # 100ms to 5s
            tool_duration.labels(server=server, tool=tool).observe(duration)

            # Generate token usage
            oci_tokens.labels(service='oci-client', operation=tool).inc(random.randint(100, 1000))

            print(f"Generated: {server}/{tool} ({outcome}) - {duration:.2f}s")

            time.sleep(random.uniform(1, 5))  # Wait 1-5 seconds between generations

    except KeyboardInterrupt:
        print("\n✅ Metrics generator stopped")

def generate_opentelemetry_traces():
    """Generate test OpenTelemetry traces"""
    try:
        from mcp_oci_common.observability import init_tracing, set_common_span_attributes
        from mcp_oci_common.otel_mcp import create_mcp_otel_enhancer

        print("🔍 Initializing OpenTelemetry tracing...")

        # Initialize tracing
        tracer = init_tracing("test-data-generator")
        enhancer = create_mcp_otel_enhancer("test-mcp-service")

        if not tracer:
            print("⚠️ OpenTelemetry not available, skipping trace generation")
            return

        servers = ['mcp-compute', 'mcp-network', 'mcp-security', 'mcp-observability']
        tools = ['list_instances', 'get_metrics', 'scan_vulnerabilities', 'analyze_traces']

        print("🔗 Generating test traces...")

        while True:
            server = random.choice(servers)
            tool = random.choice(tools)

            # Create a traced operation
            @enhancer.traced_operation(
                operation_name=f"{server}_{tool}",
                attributes={
                    "test.data": True,
                    "server.type": "mcp",
                    "operation.category": "test"
                }
            )
            def test_operation():
                # Simulate work
                time.sleep(random.uniform(0.1, 2.0))
                if random.random() < 0.1:  # 10% chance of error
                    raise Exception(f"Simulated error in {tool}")
                return f"Completed {tool}"

            try:
                result = test_operation()
                print(f"Trace generated: {server}/{tool} - {result}")
            except Exception as e:
                print(f"Trace generated with error: {server}/{tool} - {e}")

            time.sleep(random.uniform(2, 8))  # Wait 2-8 seconds between traces

    except KeyboardInterrupt:
        print("\n✅ Trace generator stopped")
    except ImportError as e:
        print(f"⚠️ Could not generate traces: {e}")

def test_observability_endpoints():
    """Test all observability endpoints to ensure they're working"""
    print("🧪 Testing observability endpoints...")

    endpoints = [
        ('Prometheus', 'http://localhost:9090/-/ready'),
        ('Prometheus Targets', 'http://localhost:9090/targets'),
        ('OTLP Collector', 'http://localhost:8889/metrics'),
        ('Jaeger Health', 'http://localhost:14269/'),
        ('Jaeger Metrics', 'http://localhost:14269/metrics'),
        ('Tempo Ready', 'http://localhost:3200/api/echo'),
        ('Tempo Metrics', 'http://localhost:3200/metrics'),
        ('Pyroscope', 'http://localhost:4040/'),
        ('Grafana Health', 'http://localhost:3000/api/health'),
    ]

    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: OK")
            else:
                print(f"⚠️ {name}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: {e}")

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate test data for observability stack')
    parser.add_argument('--mode', choices=['metrics', 'traces', 'test', 'all'],
                       default='all', help='What to generate')
    parser.add_argument('--duration', type=int, default=300,
                       help='Duration in seconds (default: 300)')

    args = parser.parse_args()

    print("🔧 MCP Observability Test Data Generator")
    print("=" * 50)

    if args.mode in ['test', 'all']:
        test_observability_endpoints()
        print()

    if args.mode in ['metrics', 'all']:
        print("Starting metrics generation...")
        try:
            generate_prometheus_metrics()
        except KeyboardInterrupt:
            print("Metrics generation stopped")

    if args.mode in ['traces', 'all']:
        print("Starting trace generation...")
        try:
            generate_opentelemetry_traces()
        except KeyboardInterrupt:
            print("Trace generation stopped")

if __name__ == "__main__":
    main()