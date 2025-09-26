from __future__ import annotations

import os
import socket
import typing as t

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
import time
try:
    from prometheus_client import Counter as _PromCounter, Histogram as _PromHistogram  # type: ignore
    _PROM_AVAILABLE = True
except Exception:
    _PROM_AVAILABLE = False

_tool_calls_counter = None
_tool_duration_histogram = None

def _get_prom_metrics():
    global _tool_calls_counter, _tool_duration_histogram
    if not _PROM_AVAILABLE:
        return None, None
    if _tool_calls_counter is None:
        _tool_calls_counter = _PromCounter(
            'mcp_tool_calls_total',
            'Total MCP tool calls',
            ['server', 'tool', 'outcome']
        )
    if _tool_duration_histogram is None:
        _tool_duration_histogram = _PromHistogram(
            'mcp_tool_duration_seconds',
            'MCP tool duration (s)',
            ['server', 'tool']
        )
    return _tool_calls_counter, _tool_duration_histogram

_DEFAULT_SERVICE_NAMESPACE = os.getenv("OTEL_SERVICE_NAMESPACE", "mcp-oci")
_DEFAULT_ENV = os.getenv("DEPLOYMENT_ENVIRONMENT", os.getenv("ENVIRONMENT", "local"))
_HOSTNAME = socket.gethostname()
_PID = os.getpid()


def _normalize_otlp_endpoint(ep: str | None) -> str | None:
    """
    Normalize OTLP gRPC endpoint. If users set http://localhost:4317, strip the scheme
    because gRPC exporters expect 'host:port' without a scheme.
    """
    if not ep:
        return ep
    if ep.startswith("http://"):
        return ep[len("http://"):]
    if ep.startswith("https://"):
        return ep[len("https://"):]
    return ep


def _build_resource(service_name: str, service_namespace: str | None = None) -> Resource:
    # Minimal semantic attributes to avoid unknown_service in Tempo
    attrs = {
        "service.name": service_name,
        "service.namespace": service_namespace or _DEFAULT_SERVICE_NAMESPACE,
        "service.instance.id": f"{_HOSTNAME}-{_PID}",
        "deployment.environment": _DEFAULT_ENV,
    }
    # Optional enrichment (if provided in env)
    if ver := os.getenv("SERVICE_VERSION"):
        attrs["service.version"] = ver
    if team := os.getenv("SERVICE_TEAM"):
        attrs["service.team"] = team
    return Resource.create(attrs)


def init_tracing(
    service_name: str,
    *,
    service_namespace: str | None = None,
    endpoint: str | None = None,
    insecure: bool = True,
) -> trace.Tracer:
    """
    Configure a global TracerProvider with a Resource including service.name to avoid 'unknown_service'.
    This is idempotent: calling it multiple times will not re-create providers.
    """
    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, TracerProvider):
        # Already initialized; return tracer for the requested service name.
        return trace.get_tracer(service_name)

    exporter_endpoint = _normalize_otlp_endpoint(endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"))
    resource = _build_resource(service_name, service_namespace)

    provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(endpoint=exporter_endpoint, insecure=insecure)
    provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


def init_metrics(
    *,
    endpoint: str | None = None,
    insecure: bool = True,
    meter_name: str = "mcp_oci_metrics",
) -> metrics.Meter:
    """
    Initialize OTLP metrics export (optional). Uses the same endpoint as tracing by default.
    This is idempotent: calling it multiple times will not re-create providers.
    """
    current_provider = metrics.get_meter_provider()
    if isinstance(current_provider, MeterProvider):
        # Already initialized; return meter for the requested name.
        return metrics.get_meter(meter_name)

    exporter_endpoint = _normalize_otlp_endpoint(endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"))
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=exporter_endpoint, insecure=insecure)
    )
    provider = MeterProvider(resource=_build_resource(meter_name), metric_readers=[metric_reader])
    metrics.set_meter_provider(provider)
    return metrics.get_meter(meter_name)


def set_common_span_attributes(
    span: trace.Span,
    *,
    mcp_server: str | None = None,
    mcp_tool: str | None = None,
    attributes: dict[str, t.Any] | None = None,
) -> None:
    """
    Attach common attributes for MCP spans so dashboards/TraceQL can group effectively.
    """
    if not span.is_recording():
        return
    if mcp_server:
        # Preferred attribute keys
        span.set_attribute("mcp.server.name", mcp_server)
        # OpenLLMetry-compatible synonym
        span.set_attribute("ai.mcp.server", mcp_server)
    if mcp_tool:
        # Preferred attribute keys
        span.set_attribute("mcp.tool.name", mcp_tool)
        # OpenLLMetry-compatible synonym
        span.set_attribute("ai.mcp.tool", mcp_tool)
    if attributes:
        for k, v in attributes.items():
            try:
                span.set_attribute(k, v)
            except Exception:
                # Be permissive on attribute typing
                span.set_attribute(k, str(v))


def add_oci_call_attributes(
    span: trace.Span,
    *,
    oci_service: str,
    oci_operation: str,
    region: str | None = None,
    endpoint: str | None = None,
    request_id: str | None = None,
) -> None:
    """
    Enrich a span with OCI call metadata so we can answer: which REST backend call was made.
    """
    set_common_span_attributes(
        span,
        attributes={
            "oci.service": oci_service,
            "oci.operation": oci_operation,
            "oci.region": region or "",
            "oci.endpoint": endpoint or "",
        },
    )
    if request_id:
        span.set_attribute("oci.request_id", request_id)


_token_counter = None

def get_token_counter():
    global _token_counter
    if not _token_counter:
        meter = metrics.get_meter("oci_mcp_metrics")
        _token_counter = meter.create_counter(
            name="oci.mcp.tokens.total",
            description="Total tokens used",
            unit="1"
        )
    return _token_counter

def record_token_usage(
    total: int,
    request: int | None = None,
    response: int | None = None,
    attrs: dict[str, t.Any] | None = None
) -> None:
    """Record token usage metrics for future LLM integrations"""
    counter = get_token_counter()
    attributes = attrs or {}
    counter.add(total, attributes)
    
    # Also add to current span if available
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute("oci.mcp.tokens.total", total)
        if request:
            span.set_attribute("oci.mcp.tokens.request", request)
        if response:
            span.set_attribute("oci.mcp.tokens.response", response)

class tool_span:
    """
    Context manager to simplify instrumenting a tool function:
        with tool_span(tracer, "list_instances", mcp_server="oci-mcp-compute"):
            ...
    """

    def __init__(self, tracer: trace.Tracer, tool_name: str, *, mcp_server: str):
        self._tracer = tracer
        self._tool_name = tool_name
        self._mcp_server = mcp_server
        self._span: trace.Span | None = None

    def __enter__(self):
        self._span = self._tracer.start_span(self._tool_name)
        set_common_span_attributes(self._span, mcp_server=self._mcp_server, mcp_tool=self._tool_name)
        try:
            self._start = time.perf_counter()
        except Exception:
            self._start = None
        return self._span

    def __exit__(self, exc_type, exc, tb):
        # Record error on span if present
        if self._span and exc:
            self._span.record_exception(exc)
            self._span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
        # Prometheus metrics for tool duration and outcome
        try:
            c, h = _get_prom_metrics()
            if h is not None and getattr(self, "_start", None) is not None:
                duration = max(0.0, time.perf_counter() - self._start)  # seconds
                h.labels(self._mcp_server, self._tool_name).observe(duration)
            if c is not None:
                outcome = "error" if exc else "success"
                c.labels(self._mcp_server, self._tool_name, outcome).inc()
        except Exception:
            pass
        if self._span:
            self._span.end()
