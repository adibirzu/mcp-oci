#!/usr/bin/env python3

import sys
import os
import time
import json

sys.path.append('.')

# Handle requests dependency gracefully for CI environments
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    import warnings
    warnings.warn(
        "requests not available. Observability pipeline tests will be skipped. "
        "Install with: pip install requests or pip install mcp-oci[test]",
        UserWarning
    )

# Set environment variables for observability
os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = 'localhost:4317'
os.environ['PYROSCOPE_SERVER_ADDRESS'] = 'http://localhost:4040'

def test_metrics_pipeline():
    """Test that metrics are flowing through the pipeline"""
    print("🔍 Testing metrics pipeline...")

    if not REQUESTS_AVAILABLE:
        print("⚠️ Skipping metrics pipeline test: requests not available")
        return False

    try:
        # Check OTLP collector metrics
        response = requests.get('http://localhost:8889/metrics')
        if response.status_code == 200:
            if 'oci_mcp_tokens_total' in response.text:
                print("✅ OTLP Collector is receiving MCP metrics")
            else:
                print("⚠️ OTLP Collector running but no MCP metrics found")
        else:
            print("❌ OTLP Collector not responding")
            return False

        # Check Prometheus
        response = requests.get('http://localhost:9090/api/v1/query?query=mcp_tool_calls_total')
        if response.status_code == 200:
            data = response.json()
            if data['data']['result']:
                print(f"✅ Prometheus has {len(data['data']['result'])} MCP tool metrics")
            else:
                print("⚠️ Prometheus responding but no MCP tool metrics")
        else:
            print("❌ Prometheus not responding")
            return False

        return True

    except Exception as e:
        print(f"❌ Metrics pipeline test failed: {e}")
        return False

def test_traces_pipeline():
    """Test that traces are flowing through the pipeline"""
    print("\n🔍 Testing traces pipeline...")

    if not REQUESTS_AVAILABLE:
        print("⚠️ Skipping traces pipeline test: requests not available")
        return False

    try:
        # Import after setting environment
        from mcp_oci_common.observability import init_tracing

        # Create test trace
        tracer = init_tracing("test-e2e-service")
        with tracer.start_span("test_e2e_operation") as span:
            span.set_attribute("mcp.server.name", "test-e2e-server")
            span.set_attribute("mcp.tool.name", "test_e2e_tool")
            span.set_attribute("test.type", "end-to-end")
            time.sleep(0.1)

        # Wait for trace export
        time.sleep(3)

        # Check Tempo for traces
        response = requests.get('http://localhost:3200/api/search?limit=10')
        if response.status_code == 200:
            data = response.json()
            if data.get('traces'):
                print(f"✅ Tempo has {len(data['traces'])} traces")
                # Look for our test trace
                test_traces = [t for t in data['traces'] if 'test-e2e' in t.get('rootServiceName', '')]
                if test_traces:
                    print("✅ Test trace found in Tempo")
                else:
                    print("⚠️ Test trace not yet visible in Tempo (may need more time)")
            else:
                print("⚠️ Tempo responding but no traces found")
        else:
            print("❌ Tempo not responding")
            return False

        return True

    except Exception as e:
        print(f"❌ Traces pipeline test failed: {e}")
        return False

def test_grafana_connectivity():
    """Test that Grafana can access all data sources"""
    print("\n🔍 Testing Grafana connectivity...")

    if not REQUESTS_AVAILABLE:
        print("⚠️ Skipping Grafana connectivity test: requests not available")
        return False

    try:
        # Check data sources
        response = requests.get(
            'http://localhost:3000/api/datasources',
            auth=('admin', 'admin')
        )

        if response.status_code == 200:
            datasources = response.json()
            ds_names = [ds['name'] for ds in datasources]
            print(f"✅ Grafana data sources: {', '.join(ds_names)}")

            # Expected data sources
            expected = ['Prometheus', 'Tempo', 'Pyroscope']
            missing = [ds for ds in expected if ds not in ds_names]
            if missing:
                print(f"⚠️ Missing data sources: {', '.join(missing)}")
            else:
                print("✅ All expected data sources configured")

            return True
        else:
            print("❌ Grafana not responding")
            return False

    except Exception as e:
        print(f"❌ Grafana connectivity test failed: {e}")
        return False

def test_service_health():
    """Test that all observability services are healthy"""
    print("\n🔍 Testing service health...")

    if not REQUESTS_AVAILABLE:
        print("⚠️ Skipping service health test: requests not available")
        return False

    services = [
        ('Grafana', 'http://localhost:3000/api/health'),
        ('Prometheus', 'http://localhost:9090/-/ready'),
        ('Tempo', 'http://localhost:3200/api/echo'),
        ('Pyroscope', 'http://localhost:4040/'),
        ('OTLP Collector', 'http://localhost:8889/metrics'),
    ]

    all_healthy = True
    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name} is healthy")
            else:
                print(f"⚠️ {name} returned status {response.status_code}")
                all_healthy = False
        except Exception as e:
            print(f"❌ {name} is not responding: {e}")
            all_healthy = False

    return all_healthy

def test_mcp_servers_metrics():
    """Test that MCP servers are exposing metrics"""
    print("\n🔍 Testing MCP server metrics...")

    if not REQUESTS_AVAILABLE:
        print("⚠️ Skipping MCP servers metrics test: requests not available")
        return False

    # Common MCP server ports
    servers = [
        ('Compute', 8001),
        ('Database', 8002),
        ('Observability', 8003),
        ('Security', 8004),
        ('Cost', 8005),
        ('Network', 8006),
        ('BlockStorage', 8007),
        ('LoadBalancer', 8008),
        ('Inventory', 8009),
        ('UX', 8010),
    ]

    healthy_servers = 0
    for name, port in servers:
        try:
            response = requests.get(f'http://localhost:{port}/metrics', timeout=2)
            if response.status_code == 200:
                print(f"✅ {name} server metrics available")
                healthy_servers += 1
            else:
                print(f"⚠️ {name} server returned status {response.status_code}")
        except Exception:
            print(f"⚠️ {name} server not responding (may be stopped)")

    print(f"📊 {healthy_servers}/{len(servers)} MCP servers are exposing metrics")
    return healthy_servers > 0

def main():
    print("🧪 MCP-OCI Observability End-to-End Test")
    print("=" * 50)

    tests = [
        ("Service Health", test_service_health),
        ("MCP Server Metrics", test_mcp_servers_metrics),
        ("Metrics Pipeline", test_metrics_pipeline),
        ("Traces Pipeline", test_traces_pipeline),
        ("Grafana Connectivity", test_grafana_connectivity),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 50)
    print("🏁 Test Results Summary")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n📊 Overall: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("\n🎉 All tests passed! Observability pipeline is fully functional.")
    elif passed >= len(tests) * 0.8:
        print("\n✅ Most tests passed! Observability pipeline is mostly functional.")
    else:
        print("\n⚠️ Some tests failed. Check individual components.")

    print("\n🌐 Access Points:")
    print("- Grafana: http://localhost:3000 (admin/admin)")
    print("- Prometheus: http://localhost:9090")
    print("- Tempo: http://localhost:3200")
    print("- Pyroscope: http://localhost:4040")
    print("- UX App: http://localhost:8010")

if __name__ == "__main__":
    main()