#!/usr/bin/env python3
"""
Test script to verify MCP server telemetry is working.
This simulates what an MCP server does when sending telemetry.
"""
import os
import sys
import time

# Set environment before importing OpenTelemetry
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "localhost:4317"
os.environ["OTEL_SERVICE_NAME"] = "test-mcp-telemetry"

# Add src to path to import mcp_oci_common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from mcp_oci_common.observability import init_tracing, init_metrics, tool_span
    from opentelemetry import trace

    print("✓ OpenTelemetry imports successful")

    # Initialize tracing and metrics
    print(f"Initializing tracing with endpoint: {os.environ['OTEL_EXPORTER_OTLP_ENDPOINT']}")
    tracer = init_tracing(service_name="test-mcp-telemetry")
    init_metrics()

    print("✓ Tracing and metrics initialized")

    # Create a test span
    print("Creating test span...")
    with tool_span(tracer, "test_operation", mcp_server="test-mcp-telemetry") as span:
        if span:
            span.set_attribute("test.attribute", "test_value")
            span.set_attribute("mcp.tool.name", "test_operation")
            print("✓ Span created and attributes set")
        time.sleep(0.1)  # Simulate some work

    print("✓ Span completed")

    # Give the exporter time to send the data
    print("Waiting for telemetry export (5 seconds)...")
    time.sleep(5)

    print("\n✅ Test completed successfully!")
    print("\nNext steps:")
    print("1. Check otel-collector logs: docker logs otel-collector --tail 50")
    print("2. Check Jaeger UI: http://localhost:16686")
    print("3. Look for service 'test-mcp-telemetry'")
    print("4. Check Prometheus metrics: curl http://localhost:8889/metrics | grep test")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you have OpenTelemetry installed:")
    print("  pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
