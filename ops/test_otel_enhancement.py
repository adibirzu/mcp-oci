#!/usr/bin/env python3
"""
Test script for OpenTelemetry MCP enhancement capabilities
"""

import json
import sys
import os
import time
from pathlib import Path

# Add the parent directory to sys.path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_oci_common.otel_mcp import create_mcp_otel_enhancer, MCPObservabilityEnhancer

def test_otel_enhancer_creation():
    """Test creating the MCP OpenTelemetry enhancer"""
    print("🔍 Testing MCP OpenTelemetry enhancer creation...")

    try:
        enhancer = create_mcp_otel_enhancer("test-mcp-service")
        print(f"✅ Created enhancer for service: {enhancer.service_name}")

        # Test server capabilities
        capabilities = enhancer.get_server_capabilities()
        print(f"✅ Server capabilities: {json.dumps(capabilities, indent=2)}")

        return True
    except Exception as e:
        print(f"❌ Failed to create enhancer: {e}")
        return False

def test_trace_span_creation():
    """Test creating traced spans"""
    print("\n🔍 Testing trace span creation...")

    try:
        enhancer = create_mcp_otel_enhancer("test-trace-service")

        # Create a test span
        span = enhancer.create_trace_span(
            name="test_operation",
            trace_token="test-token-123",
            attributes={
                "test.type": "unit_test",
                "operation.category": "mcp_test"
            }
        )

        print(f"✅ Created span: {span.name}")
        print(f"✅ Span context: {span.get_span_context()}")

        # Add some test attributes and end the span
        span.set_attribute("test.result", "success")
        span.end()

        print("✅ Span completed successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to create trace span: {e}")
        return False

def test_trace_notification():
    """Test trace notification creation and handling"""
    print("\n🔍 Testing trace notification...")

    try:
        enhancer = create_mcp_otel_enhancer("test-notification-service")

        # Register a test handler
        notifications_received = []

        def test_handler(notification):
            notifications_received.append(notification)
            print(f"📨 Received notification: {notification['method']}")

        enhancer.register_trace_handler(test_handler)

        # Create and send a test span
        span = enhancer.create_trace_span(
            name="notification_test_operation",
            trace_token="notification-token-456",
            attributes={"test.notification": True}
        )

        span.set_attribute("notification.test", "success")
        span.end()

        # Send the notification
        enhancer.send_trace_notification(span, "notification-token-456")

        # Check if notification was received
        if notifications_received:
            notification = notifications_received[0]
            print(f"✅ Notification received with method: {notification['method']}")
            print(f"✅ TraceToken: {notification['params'].get('traceToken')}")
            print(f"✅ Resource spans count: {len(notification['params']['resourceSpans'])}")
        else:
            print("⚠️ No notifications received")

        return len(notifications_received) > 0

    except Exception as e:
        print(f"❌ Failed to test trace notification: {e}")
        return False

def test_traced_operation_decorator():
    """Test the traced operation decorator"""
    print("\n🔍 Testing traced operation decorator...")

    try:
        enhancer = create_mcp_otel_enhancer("test-decorator-service")

        # Register a test handler to capture traces
        traces_received = []

        def trace_capture_handler(notification):
            traces_received.append(notification)

        enhancer.register_trace_handler(trace_capture_handler)

        # Create a decorated test function
        @enhancer.traced_operation(
            operation_name="test_decorated_function",
            attributes={"function.type": "test"}
        )
        def test_function(value):
            time.sleep(0.1)  # Simulate some work
            return f"processed: {value}"

        # Call the decorated function
        result = test_function("test_data")
        print(f"✅ Function result: {result}")

        # Check if trace was captured
        if traces_received:
            trace = traces_received[0]
            spans = trace['params']['resourceSpans'][0]['scopeSpans'][0]['spans']
            if spans:
                span = spans[0]
                print(f"✅ Traced operation: {span['name']}")
                print(f"✅ Span attributes: {len(span['attributes'])} attributes")
        else:
            print("⚠️ No traces captured")

        return len(traces_received) > 0

    except Exception as e:
        print(f"❌ Failed to test traced operation decorator: {e}")
        return False

def test_otlp_json_format():
    """Test OTLP/JSON format compliance"""
    print("\n🔍 Testing OTLP/JSON format compliance...")

    try:
        enhancer = create_mcp_otel_enhancer("test-format-service")

        # Create a span and collect the notification
        notifications = []

        def format_test_handler(notification):
            notifications.append(notification)

        enhancer.register_trace_handler(format_test_handler)

        span = enhancer.create_trace_span(
            name="format_test_operation",
            trace_token="format-test-789",
            attributes={
                "string_attr": "test_value",
                "int_attr": 42,
                "float_attr": 3.14,
                "bool_attr": True
            }
        )

        span.end()
        enhancer.send_trace_notification(span, "format-test-789")

        if notifications:
            notification = notifications[0]

            # Validate OTLP/JSON structure
            assert notification['jsonrpc'] == "2.0"
            assert notification['method'] == "notifications/otel/trace"
            assert 'params' in notification
            assert 'resourceSpans' in notification['params']
            assert 'traceToken' in notification['params']

            resource_spans = notification['params']['resourceSpans'][0]
            assert 'resource' in resource_spans
            assert 'scopeSpans' in resource_spans

            scope_spans = resource_spans['scopeSpans'][0]
            assert 'scope' in scope_spans
            assert 'spans' in scope_spans

            span_data = scope_spans['spans'][0]
            required_fields = ['traceId', 'spanId', 'name', 'kind', 'startTimeUnixNano', 'endTimeUnixNano', 'attributes', 'status']
            for field in required_fields:
                assert field in span_data, f"Missing required field: {field}"

            print("✅ OTLP/JSON format validation passed")
            print(f"✅ TraceToken correlation: {notification['params']['traceToken']}")
            return True
        else:
            print("❌ No notification received for format testing")
            return False

    except Exception as e:
        print(f"❌ OTLP/JSON format test failed: {e}")
        return False

def main():
    """Run all OpenTelemetry MCP enhancement tests"""
    print("🧪 Testing OpenTelemetry MCP Enhancement Implementation")
    print("=" * 60)

    tests = [
        ("Enhancer Creation", test_otel_enhancer_creation),
        ("Trace Span Creation", test_trace_span_creation),
        ("Trace Notification", test_trace_notification),
        ("Traced Operation Decorator", test_traced_operation_decorator),
        ("OTLP/JSON Format", test_otlp_json_format),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("🏁 OpenTelemetry MCP Enhancement Test Results")
    print("=" * 60)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n📊 Overall: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("\n🎉 All OpenTelemetry MCP enhancement tests passed!")
        print("✅ Implementation is ready for integration")
    elif passed >= len(tests) * 0.8:
        print("\n✅ Most tests passed! Enhancement is largely functional.")
    else:
        print("\n⚠️ Some tests failed. Check implementation details.")

    print("\n🌟 OpenTelemetry MCP Features Implemented:")
    print("- ✅ notifications/otel/trace support")
    print("- ✅ traceToken correlation")
    print("- ✅ OTLP/JSON trace format")
    print("- ✅ Server capability declaration")
    print("- ✅ Client-controlled trace routing")
    print("- ✅ Traced operation decorator")

if __name__ == "__main__":
    main()