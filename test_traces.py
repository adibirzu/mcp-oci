#!/usr/bin/env python3

import sys
import os
import time
sys.path.append('.')

# Set environment variables
os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = 'localhost:4317'

from mcp_oci_common.observability import init_tracing

def test_tracing():
    print("🔍 Testing trace export...")

    # Initialize tracing
    tracer = init_tracing("test-mcp-server")
    print("✅ Tracer initialized")

    # Create some test spans
    with tracer.start_span("test_operation") as span:
        span.set_attribute("mcp.server.name", "test-server")
        span.set_attribute("mcp.tool.name", "test_tool")
        span.set_attribute("test.attribute", "test_value")

        time.sleep(0.1)  # Simulate some work

        with tracer.start_span("nested_operation", context=None) as nested_span:
            nested_span.set_attribute("nested", True)
            time.sleep(0.05)

    print("✅ Created test spans")

    # Force flush traces
    time.sleep(2)
    print("✅ Traces should be exported now")

if __name__ == "__main__":
    test_tracing()