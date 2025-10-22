#!/usr/bin/env python3
"""
OpenTelemetry MCP Enhancement Implementation

This module implements the OpenTelemetry proposal for MCP from:
https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/269

Features:
- notifications/otel/trace support
- traceToken correlation
- OTLP/JSON trace format
- Server capability declaration
- Client-controlled trace routing
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider, Span


@dataclass
class OTelAttribute:
    """OpenTelemetry attribute in OTLP/JSON format"""

    key: str
    value: Any

    def to_dict(self) -> Dict[str, Any]:
        """Convert to OTLP/JSON format"""
        value_type = "stringValue"
        value_data = str(self.value)

        if isinstance(self.value, int):
            value_type = "intValue"
            value_data = self.value
        elif isinstance(self.value, float):
            value_type = "doubleValue"
            value_data = self.value
        elif isinstance(self.value, bool):
            value_type = "boolValue"
            value_data = self.value

        return {"key": self.key, "value": {value_type: value_data}}


@dataclass
class OTelStatus:
    """OpenTelemetry status in OTLP/JSON format"""

    code: int = 0  # 0=UNSET, 1=OK, 2=ERROR
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to OTLP/JSON format"""
        result = {"code": self.code}
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class OTelSpan:
    """OpenTelemetry span in OTLP/JSON format"""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    start_time_unix_nano: int
    end_time_unix_nano: int
    attributes: List[OTelAttribute]
    status: OTelStatus
    kind: int = 1  # SPAN_KIND_SERVER

    def to_dict(self) -> Dict[str, Any]:
        """Convert to OTLP/JSON format"""
        span_dict = {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "name": self.name,
            "kind": self.kind,
            "startTimeUnixNano": str(self.start_time_unix_nano),
            "endTimeUnixNano": str(self.end_time_unix_nano),
            "attributes": [attr.to_dict() for attr in self.attributes],
            "status": self.status.to_dict(),
        }

        if self.parent_span_id:
            span_dict["parentSpanId"] = self.parent_span_id

        return span_dict


@dataclass
class OTelTraceNotification:
    """MCP OpenTelemetry trace notification"""

    method: str = "notifications/otel/trace"
    params: Dict[str, Any] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP notification format"""
        return {"jsonrpc": "2.0", "method": self.method, "params": self.params}


class MCPTraceCollector:
    """Collects and formats OpenTelemetry traces for MCP notifications"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.collected_spans: List[OTelSpan] = []

    def collect_span_from_otel(
        self, span: Span, trace_token: Optional[str] = None
    ) -> OTelSpan:
        """Convert OpenTelemetry span to MCP format"""

        # Extract span context
        span_context = span.get_span_context()
        trace_id = f"{span_context.trace_id:032x}"
        span_id = f"{span_context.span_id:016x}"

        # Get parent span ID if available
        parent_span_id = None
        if hasattr(span, "parent") and span.parent:
            parent_span_id = f"{span.parent.span_id:016x}"

        # Convert attributes
        attributes = []
        if hasattr(span, "attributes") and span.attributes:
            for key, value in span.attributes.items():
                attributes.append(OTelAttribute(key=key, value=value))

        # Add MCP-specific attributes
        attributes.extend(
            [
                OTelAttribute(key="mcp.service.name", value=self.service_name),
                OTelAttribute(key="mcp.server.type", value="oci-mcp"),
            ]
        )

        if trace_token:
            attributes.append(OTelAttribute(key="mcp.trace.token", value=trace_token))

        # Convert status
        status_code = 0  # UNSET
        status_message = None
        if hasattr(span, "status") and span.status:
            if span.status.status_code == StatusCode.OK:
                status_code = 1
            elif span.status.status_code == StatusCode.ERROR:
                status_code = 2
                status_message = span.status.description

        status = OTelStatus(code=status_code, message=status_message)

        # Get timing
        start_time = int(
            getattr(span, "start_time", time.time()) * 1_000_000_000
        )  # Convert to nanoseconds
        end_time = int(getattr(span, "end_time", time.time()) * 1_000_000_000)

        # Get span name safely
        span_name = getattr(span, "name", "unknown_operation")

        return OTelSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            name=span_name,
            start_time_unix_nano=start_time,
            end_time_unix_nano=end_time,
            attributes=attributes,
            status=status,
        )

    def create_notification(
        self, spans: List[OTelSpan], trace_token: Optional[str] = None
    ) -> OTelTraceNotification:
        """Create MCP trace notification"""

        params = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            OTelAttribute(
                                key="service.name", value=self.service_name
                            ).to_dict(),
                            OTelAttribute(
                                key="service.version", value="1.0.0"
                            ).to_dict(),
                            OTelAttribute(
                                key="mcp.server.name", value=self.service_name
                            ).to_dict(),
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {
                                "name": "mcp-otel-enhancement",
                                "version": "1.0.0",
                            },
                            "spans": [span.to_dict() for span in spans],
                        }
                    ],
                }
            ]
        }

        if trace_token:
            params["traceToken"] = trace_token

        return OTelTraceNotification(params=params)


class MCPObservabilityEnhancer:
    """Enhanced MCP observability with OpenTelemetry proposal implementation"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.trace_collector = MCPTraceCollector(service_name)
        self.capabilities = {"otel": {"traces": True}}
        self.trace_handlers: List[callable] = []

        # Initialize OpenTelemetry with a proper TracerProvider
        self._init_tracer_provider()

    def _init_tracer_provider(self):
        """Initialize OpenTelemetry TracerProvider for real span creation"""
        # Set up a TracerProvider to ensure we get recording spans
        # Only initialize if no tracer provider is already set
        if not hasattr(trace.get_tracer_provider(), "_resource"):
            tracer_provider = TracerProvider()
            trace.set_tracer_provider(tracer_provider)

    def register_trace_handler(self, handler: callable):
        """Register handler for trace notifications"""
        self.trace_handlers.append(handler)

    def get_server_capabilities(self) -> Dict[str, Any]:
        """Get enhanced server capabilities including otel.traces"""
        return self.capabilities

    def create_trace_span(
        self,
        name: str,
        trace_token: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        parent_span: Optional[Span] = None,
    ) -> Span:
        """Create traced span with MCP enhancement"""

        tracer = trace.get_tracer(self.service_name)

        # Create span with attributes
        span_attributes = {
            "mcp.service.name": self.service_name,
            "mcp.operation.name": name,
        }

        if trace_token:
            span_attributes["mcp.trace.token"] = trace_token

        if attributes:
            span_attributes.update(attributes)

        span = tracer.start_span(name=name, attributes=span_attributes)

        return span

    def send_trace_notification(self, span: Span, trace_token: Optional[str] = None):
        """Send trace notification to registered handlers"""

        # Convert span to MCP format
        mcp_span = self.trace_collector.collect_span_from_otel(span, trace_token)

        # Create notification
        notification = self.trace_collector.create_notification([mcp_span], trace_token)

        # Send to handlers
        for handler in self.trace_handlers:
            try:
                handler(notification.to_dict())
            except Exception as e:
                # Don't let trace handling break the main application
                print(f"Warning: Trace handler failed: {e}")

    def traced_operation(
        self,
        operation_name: str,
        trace_token: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Decorator for traced MCP operations"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                # Extract trace token from request if not provided
                request_trace_token = trace_token
                if (
                    not trace_token
                    and args
                    and hasattr(args[0], "meta")
                    and args[0].meta
                ):
                    request_trace_token = args[0].meta.get("traceToken")

                # Create span
                span = self.create_trace_span(
                    name=operation_name,
                    trace_token=request_trace_token,
                    attributes=attributes,
                )

                try:
                    # Execute operation
                    result = func(*args, **kwargs)

                    # Mark span as successful
                    span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    # Mark span as error
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("error.message", str(e))
                    span.set_attribute("error.type", type(e).__name__)
                    raise

                finally:
                    # End span and send notification
                    span.end()
                    self.send_trace_notification(span, request_trace_token)

            return wrapper

        return decorator


def create_mcp_otel_enhancer(service_name: str) -> MCPObservabilityEnhancer:
    """Factory function to create MCP OpenTelemetry enhancer"""
    return MCPObservabilityEnhancer(service_name)


# Example usage and integration helpers
def enhance_mcp_server_with_otel(
    server_name: str, trace_endpoint: Optional[str] = None
):
    """Enhance existing MCP server with OpenTelemetry capabilities"""

    enhancer = create_mcp_otel_enhancer(server_name)

    # If trace endpoint provided, add HTTP handler
    if trace_endpoint:
        import requests

        def http_trace_handler(notification: Dict[str, Any]):
            """Send trace notifications via HTTP"""
            try:
                requests.post(
                    trace_endpoint,
                    json=notification,
                    headers={"Content-Type": "application/json"},
                    timeout=5,
                )
            except Exception as e:
                print(f"Failed to send trace notification: {e}")

        enhancer.register_trace_handler(http_trace_handler)

    return enhancer


if __name__ == "__main__":
    # Example usage
    enhancer = create_mcp_otel_enhancer("mcp-oci-example")

    # Example notification
    span = enhancer.create_trace_span("example_operation", "trace-123")
    span.set_attribute("tool.name", "list_instances")
    span.set_attribute("region", "us-phoenix-1")
    span.end()

    enhancer.send_trace_notification(span, "trace-123")

    print("MCP OpenTelemetry enhancement example completed!")
