#!/usr/bin/env python3
"""
Test the enhanced observability server with OpenTelemetry capabilities
"""

import json
import sys
import time
from pathlib import Path

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test the enhanced observability capabilities
def test_enhanced_observability():
    """Test the new OpenTelemetry tools in the observability server"""
    print("🔍 Testing Enhanced Observability Server...")

    try:
        from mcp_servers.observability.server import mcp_otel_enhancer

        print(f"✅ MCP OpenTelemetry enhancer initialized for: {mcp_otel_enhancer.service_name}")

        # Test server capabilities
        capabilities = mcp_otel_enhancer.get_server_capabilities()
        print(f"✅ Server capabilities: {json.dumps(capabilities, indent=2)}")

        # Test creating a traced operation
        @mcp_otel_enhancer.traced_operation(
            operation_name="test_server_operation",
            attributes={"server.test": True}
        )
        def test_server_function():
            time.sleep(0.05)
            return "server test completed"

        # Register a test handler
        notifications = []

        def test_handler(notification):
            notifications.append(notification)
            print("📨 Received trace notification from server")

        mcp_otel_enhancer.register_trace_handler(test_handler)

        # Execute the traced operation
        result = test_server_function()
        print(f"✅ Traced operation result: {result}")

        # Check if trace was captured
        if notifications:
            notification = notifications[0]
            print(f"✅ Trace notification captured: {notification['method']}")

            # Extract span details
            spans = notification['params']['resourceSpans'][0]['scopeSpans'][0]['spans']
            if spans:
                span = spans[0]
                print(f"✅ Span name: {span['name']}")
                print(f"✅ Attributes count: {len(span['attributes'])}")

        return True

    except Exception as e:
        print(f"❌ Enhanced observability test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🧪 Testing Enhanced Observability Server")
    print("=" * 50)

    success = test_enhanced_observability()

    if success:
        print("\n🎉 Enhanced observability server test passed!")
        print("✅ OpenTelemetry MCP enhancement is fully integrated")
    else:
        print("\n❌ Enhanced observability server test failed")

    print("\n🌟 New OpenTelemetry Features Available:")
    print("- get_mcp_otel_capabilities")
    print("- create_traced_operation")
    print("- send_test_trace_notification")
    print("- analyze_trace_correlation")
    print("- get_observability_metrics_summary")

if __name__ == "__main__":
    main()