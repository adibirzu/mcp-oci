from __future__ import annotations

import os
import socket
import typing as t
import warnings
import time

# Load .env.local early, before any environment variable access
try:
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Find repo root (3 levels up from mcp_oci_common/)
    _repo_root = Path(__file__).resolve().parents[2]
    # Load .env.local first (highest priority)
    load_dotenv(_repo_root / ".env.local", override=False)
except Exception:
    # dotenv not available or path issues - continue without it
    pass


class ObservabilityImportError(ImportError):
    """Custom exception for observability dependency import failures with actionable guidance."""

    def __init__(self, dependency: str, operation: str, original_error: Exception):
        self.dependency = dependency
        self.operation = operation
        self.original_error = original_error

        message = f"""
Failed to import {dependency} for {operation}.

This likely means observability dependencies are not installed. To fix this:

1. Install observability dependencies:
   pip install opentelemetry-api opentelemetry-sdk
   pip install opentelemetry-exporter-otlp-proto-grpc
   pip install prometheus-client

2. Or install with optional dependencies:
   pip install "mcp-oci[observability]"

3. For development with all dependencies:
   pip install "mcp-oci[dev]"

Original error: {original_error}

Note: Core MCP functionality works without observability dependencies.
Observability features will be disabled gracefully when dependencies are missing.
"""
        super().__init__(message)


# Lazy import flags and objects
_OTEL_AVAILABLE = None
_PROM_AVAILABLE = None
_otel_modules = {}
_prom_modules = {}


def _lazy_import_opentelemetry():
    """Lazy import of OpenTelemetry with informative error handling."""
    global _OTEL_AVAILABLE, _otel_modules

    if _OTEL_AVAILABLE is not None:
        return _OTEL_AVAILABLE, _otel_modules

    try:
        from opentelemetry import trace, metrics
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource

        # Prefer HTTP/protobuf exporters when available (OCI APM endpoint is HTTP).
        # Fall back to gRPC exporters (typical localhost collector setups).
        OTLPSpanExporterGrpc = None
        OTLPMetricExporterGrpc = None
        OTLPSpanExporterHttp = None
        OTLPMetricExporterHttp = None

        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore
                OTLPSpanExporter as _OTLPSpanExporterHttp,
            )
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import (  # type: ignore
                OTLPMetricExporter as _OTLPMetricExporterHttp,
            )

            OTLPSpanExporterHttp = _OTLPSpanExporterHttp
            OTLPMetricExporterHttp = _OTLPMetricExporterHttp
        except Exception:
            # HTTP exporters are optional
            pass

        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore
                OTLPSpanExporter as _OTLPSpanExporterGrpc,
            )
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (  # type: ignore
                OTLPMetricExporter as _OTLPMetricExporterGrpc,
            )

            OTLPSpanExporterGrpc = _OTLPSpanExporterGrpc
            OTLPMetricExporterGrpc = _OTLPMetricExporterGrpc
        except Exception:
            # gRPC exporters are optional
            pass

        _otel_modules = {
            "trace": trace,
            "metrics": metrics,
            "TracerProvider": TracerProvider,
            "BatchSpanProcessor": BatchSpanProcessor,
            "MeterProvider": MeterProvider,
            "PeriodicExportingMetricReader": PeriodicExportingMetricReader,
            "OTLPSpanExporterGrpc": OTLPSpanExporterGrpc,
            "OTLPMetricExporterGrpc": OTLPMetricExporterGrpc,
            "OTLPSpanExporterHttp": OTLPSpanExporterHttp,
            "OTLPMetricExporterHttp": OTLPMetricExporterHttp,
            "Resource": Resource,
        }
        _OTEL_AVAILABLE = True
        return True, _otel_modules

    except ImportError as e:
        _OTEL_AVAILABLE = False
        warnings.warn(
            f"OpenTelemetry not available: {e}. "
            "Tracing and metrics will be disabled. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc",
            UserWarning,
            stacklevel=2,
        )
        return False, {}


def _lazy_import_prometheus():
    """Lazy import of Prometheus client with informative error handling."""
    global _PROM_AVAILABLE, _prom_modules

    if _PROM_AVAILABLE is not None:
        return _PROM_AVAILABLE, _prom_modules

    try:
        from prometheus_client import (
            Counter as _PromCounter,
            Histogram as _PromHistogram,
        )

        _prom_modules = {
            "Counter": _PromCounter,
            "Histogram": _PromHistogram,
        }
        _PROM_AVAILABLE = True
        return True, _prom_modules

    except ImportError as e:
        _PROM_AVAILABLE = False
        warnings.warn(
            f"Prometheus client not available: {e}. "
            "Prometheus metrics will be disabled. "
            "Install with: pip install prometheus-client",
            UserWarning,
            stacklevel=2,
        )
        return False, {}


def is_observability_available() -> bool:
    """Check if observability dependencies are available."""
    otel_available, _ = _lazy_import_opentelemetry()
    prom_available, _ = _lazy_import_prometheus()
    return otel_available or prom_available


def is_opentelemetry_available() -> bool:
    """Check if OpenTelemetry dependencies are available."""
    available, _ = _lazy_import_opentelemetry()
    return available


def is_prometheus_available() -> bool:
    """Check if Prometheus client is available."""
    available, _ = _lazy_import_prometheus()
    return available


_tool_calls_counter = None
_tool_duration_histogram = None


def _get_prom_metrics():
    """Get Prometheus metrics with lazy import and graceful fallback."""
    global _tool_calls_counter, _tool_duration_histogram

    prom_available, prom_modules = _lazy_import_prometheus()
    if not prom_available:
        return None, None

    if _tool_calls_counter is None:
        _tool_calls_counter = prom_modules["Counter"](
            "mcp_tool_calls_total",
            "Total MCP tool calls",
            ["server", "tool", "outcome"],
        )
    if _tool_duration_histogram is None:
        _tool_duration_histogram = prom_modules["Histogram"](
            "mcp_tool_duration_seconds", "MCP tool duration (s)", ["server", "tool"]
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
        return ep[len("http://") :]
    if ep.startswith("https://"):
        return ep[len("https://") :]
    return ep


def _otel_tracing_enabled() -> bool:
    return os.getenv("OTEL_TRACING_ENABLED", "true").lower() == "true"


def _infer_otlp_transport(endpoint: str) -> str:
    # OCI APM endpoints are HTTPS URLs with a path like /20200101/opentelemetry.
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return "http"
    return "grpc"


def _normalize_oci_apm_endpoint(endpoint: str, signal: str) -> str:
    """
    Normalize OCI APM OTLP endpoints to the expected OTLP signal paths.
    Mirrors the Node agents' behavior for /opentelemetry/private/v1/{signal}.
    """
    base = endpoint.rstrip("/")
    if "/v1/" in base:
        return base
    if "/opentelemetry" in base:
        return f"{base}/private/v1/{signal}"
    if "/20200101" in base:
        return f"{base}/opentelemetry/private/v1/{signal}"
    return f"{base}/20200101/opentelemetry/private/v1/{signal}"


def _get_otlp_export_config(
    endpoint: str | None, *, signal: str = "traces"
) -> tuple[str, str, dict[str, str] | None]:
    """
    Determine OTLP exporter transport + endpoint + headers.

    Priority:
    1) explicit `endpoint` argument
    2) OCI APM env vars (OCI_APM_ENDPOINT) - takes precedence when available
    3) OTEL_EXPORTER_OTLP_ENDPOINT env var
    4) Local collector fallback (only if OCI APM not configured and local not disabled)
    """
    ep = endpoint
    headers: dict[str, str] | None = None

    # Prioritize OCI APM configuration
    if _otel_tracing_enabled():
        oci_ep = os.getenv("OCI_APM_ENDPOINT")
        oci_key = os.getenv("OCI_APM_PRIVATE_DATA_KEY")
        if oci_ep and oci_key:
            # OCI APM takes precedence
            ep = _normalize_oci_apm_endpoint(oci_ep, signal)
            headers = {"Authorization": f"dataKey {oci_key}"}
            # Ensure we use HTTP protocol for OCI APM
            transport = _infer_otlp_transport(ep)
            return transport, ep, headers

    # Fall back to explicit OTEL endpoint if OCI APM not configured
    if not ep:
        ep = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    # If local OTEL is disabled and no endpoint configured, disable tracing
    if not ep and os.getenv("OTEL_DISABLE_LOCAL", "false").lower() == "true":
        return "none", "", None

    # Final fallback to local collector (only if not disabled)
    if not ep:
        if os.getenv("OTEL_DISABLE_LOCAL", "false").lower() != "true":
            # Keep backwards compatibility with local collector defaults.
            ep = "localhost:4317"
        else:
            # Local disabled and no endpoint - disable tracing
            return "none", "", None

    transport = _infer_otlp_transport(ep)

    # Allow explicit OTLP headers (overrides OCI APM headers if set)
    raw_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    if raw_headers:
        parsed: dict[str, str] = {}
        for part in raw_headers.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                parsed[k.strip()] = v.strip()
        if parsed:
            headers = parsed

    return transport, ep, headers


def _build_resource(service_name: str, service_namespace: str | None = None):
    """Build OpenTelemetry resource with lazy import and graceful fallback."""
    otel_available, otel_modules = _lazy_import_opentelemetry()
    if not otel_available:
        return None

    Resource = otel_modules["Resource"]

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
):
    """
    Configure a global TracerProvider with a Resource including service.name to avoid 'unknown_service'.
    This is idempotent: calling it multiple times will not re-create providers.
    Returns None if OpenTelemetry is not available.
    """
    if not _otel_tracing_enabled():
        return None

    otel_available, otel_modules = _lazy_import_opentelemetry()
    if not otel_available:
        warnings.warn(
            f"Skipping tracing initialization for {service_name}: OpenTelemetry not available",
            UserWarning,
            stacklevel=2,
        )
        return None

    trace = otel_modules["trace"]
    TracerProvider = otel_modules["TracerProvider"]
    BatchSpanProcessor = otel_modules["BatchSpanProcessor"]

    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, TracerProvider):
        # Already initialized; return tracer for the requested service name.
        return trace.get_tracer(service_name)

    transport, exporter_endpoint, headers = _get_otlp_export_config(endpoint, signal="traces")
    
    # If transport is "none", tracing is disabled
    if transport == "none":
        warnings.warn(
            f"Tracing disabled for {service_name}: No OTLP endpoint configured and local OTEL disabled",
            UserWarning,
            stacklevel=2,
        )
        return None
    
    resource = _build_resource(service_name, service_namespace)

    try:
        provider = TracerProvider(resource=resource)
        if transport == "http":
            exporter_cls = otel_modules.get("OTLPSpanExporterHttp")
            if not exporter_cls:
                raise RuntimeError(
                    "HTTP OTLP exporter not installed. Install `opentelemetry-exporter-otlp-proto-http`."
                )
            span_exporter = exporter_cls(endpoint=exporter_endpoint, headers=headers)
        else:
            exporter_cls = otel_modules.get("OTLPSpanExporterGrpc")
            if not exporter_cls:
                raise RuntimeError(
                    "gRPC OTLP exporter not installed. Install `opentelemetry-exporter-otlp-proto-grpc`."
                )
            span_exporter = exporter_cls(
                endpoint=_normalize_otlp_endpoint(exporter_endpoint), insecure=insecure
            )
        provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(provider)
        return trace.get_tracer(service_name)
    except Exception as e:
        warnings.warn(
            f"Failed to initialize tracing for {service_name}: {e}",
            UserWarning,
            stacklevel=2,
        )
        return None


def _is_oci_apm_endpoint() -> bool:
    """Check if OCI APM endpoint is configured (OCI APM doesn't support metrics)."""
    oci_ep = os.getenv("OCI_APM_ENDPOINT")
    oci_key = os.getenv("OCI_APM_PRIVATE_DATA_KEY")
    return bool(oci_ep and oci_key)


def _metrics_exporter_disabled() -> bool:
    """Check if metrics exporter is explicitly disabled via environment."""
    # Support both MCP_OTEL_METRICS_EXPORTER=none and OTEL_METRICS_EXPORTER=none
    mcp_metrics = os.getenv("MCP_OTEL_METRICS_EXPORTER", "").lower()
    otel_metrics = os.getenv("OTEL_METRICS_EXPORTER", "").lower()
    return mcp_metrics == "none" or otel_metrics == "none"


def init_metrics(
    *,
    endpoint: str | None = None,
    insecure: bool = True,
    meter_name: str = "mcp_oci_metrics",
):
    """
    Initialize OTLP metrics export (optional). Uses the same endpoint as tracing by default.
    This is idempotent: calling it multiple times will not re-create providers.
    Returns None if OpenTelemetry is not available.

    Note: OCI APM does not support OTLP metrics - only traces. When OCI APM is configured,
    metrics export is automatically disabled to avoid 404 errors.
    """
    if not _otel_tracing_enabled():
        return None

    # Check if metrics exporter is explicitly disabled
    if _metrics_exporter_disabled():
        return None

    # OCI APM does not support OTLP metrics - skip metrics initialization
    if _is_oci_apm_endpoint():
        import logging
        logging.getLogger(__name__).debug(
            "Skipping OTLP metrics initialization: OCI APM only supports traces, not metrics"
        )
        return None

    otel_available, otel_modules = _lazy_import_opentelemetry()
    if not otel_available:
        warnings.warn(
            f"Skipping metrics initialization for {meter_name}: OpenTelemetry not available",
            UserWarning,
            stacklevel=2,
        )
        return None

    metrics = otel_modules["metrics"]
    MeterProvider = otel_modules["MeterProvider"]
    PeriodicExportingMetricReader = otel_modules["PeriodicExportingMetricReader"]

    current_provider = metrics.get_meter_provider()
    if isinstance(current_provider, MeterProvider):
        # Already initialized; return meter for the requested name.
        return metrics.get_meter(meter_name)

    transport, exporter_endpoint, headers = _get_otlp_export_config(endpoint, signal="metrics")

    # If transport is "none", metrics are disabled
    if transport == "none":
        return None

    try:
        if transport == "http":
            exporter_cls = otel_modules.get("OTLPMetricExporterHttp")
            if not exporter_cls:
                raise RuntimeError(
                    "HTTP OTLP metric exporter not installed. Install `opentelemetry-exporter-otlp-proto-http`."
                )
            metric_exporter = exporter_cls(endpoint=exporter_endpoint, headers=headers)
        else:
            exporter_cls = otel_modules.get("OTLPMetricExporterGrpc")
            if not exporter_cls:
                raise RuntimeError(
                    "gRPC OTLP metric exporter not installed. Install `opentelemetry-exporter-otlp-proto-grpc`."
                )
            metric_exporter = exporter_cls(
                endpoint=_normalize_otlp_endpoint(exporter_endpoint), insecure=insecure
            )
        metric_reader = PeriodicExportingMetricReader(
            metric_exporter
        )
        provider = MeterProvider(
            resource=_build_resource(meter_name), metric_readers=[metric_reader]
        )
        metrics.set_meter_provider(provider)
        return metrics.get_meter(meter_name)
    except Exception as e:
        warnings.warn(
            f"Failed to initialize metrics for {meter_name}: {e}",
            UserWarning,
            stacklevel=2,
        )
        return None


def set_common_span_attributes(
    span,  # Can be None if OpenTelemetry is not available
    *,
    mcp_server: str | None = None,
    mcp_tool: str | None = None,
    attributes: dict[str, t.Any] | None = None,
) -> None:
    """
    Attach common attributes for MCP spans so dashboards/TraceQL can group effectively.
    Gracefully handles None spans when OpenTelemetry is not available.
    """
    if span is None or not hasattr(span, "is_recording") or not span.is_recording():
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
    span,  # Can be None if OpenTelemetry is not available
    *,
    oci_service: str,
    oci_operation: str,
    region: str | None = None,
    endpoint: str | None = None,
    request_id: str | None = None,
) -> None:
    """
    Enrich a span with OCI call metadata so we can answer: which REST backend call was made.
    Gracefully handles None spans when OpenTelemetry is not available.
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
    if span and request_id and hasattr(span, "set_attribute"):
        span.set_attribute("oci.request_id", request_id)


_token_counter = None


def get_token_counter():
    """Get token counter with graceful fallback for missing OpenTelemetry."""
    global _token_counter

    otel_available, otel_modules = _lazy_import_opentelemetry()
    if not otel_available:
        return None

    if not _token_counter:
        metrics = otel_modules["metrics"]
        meter = metrics.get_meter("oci_mcp_metrics")
        _token_counter = meter.create_counter(
            name="oci.mcp.tokens.total", description="Total tokens used", unit="1"
        )
    return _token_counter


def record_token_usage(
    total: int,
    request: int | None = None,
    response: int | None = None,
    attrs: dict[str, t.Any] | None = None,
) -> None:
    """Record token usage metrics for future LLM integrations. Gracefully handles missing OpenTelemetry."""
    counter = get_token_counter()
    if counter:
        attributes = attrs or {}
        counter.add(total, attributes)

    # Also add to current span if available
    otel_available, otel_modules = _lazy_import_opentelemetry()
    if otel_available:
        trace = otel_modules["trace"]
        span = trace.get_current_span()
        if span and hasattr(span, "is_recording") and span.is_recording():
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
    Gracefully handles None tracer when OpenTelemetry is not available.
    """

    def __init__(self, tracer, tool_name: str, *, mcp_server: str):
        self._tracer = tracer  # Can be None if OpenTelemetry is not available
        self._tool_name = tool_name
        self._mcp_server = mcp_server
        self._span = None

    def __enter__(self):
        if self._tracer and hasattr(self._tracer, "start_span"):
            self._span = self._tracer.start_span(self._tool_name)
            set_common_span_attributes(
                self._span, mcp_server=self._mcp_server, mcp_tool=self._tool_name
            )
        else:
            self._span = None

        try:
            self._start = time.perf_counter()
        except Exception:
            self._start = None
        return self._span

    def __exit__(self, exc_type, exc, tb):
        # Record error on span if present and OpenTelemetry is available
        if self._span and exc and hasattr(self._span, "record_exception"):
            otel_available, otel_modules = _lazy_import_opentelemetry()
            if otel_available:
                trace = otel_modules["trace"]
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

        if self._span and hasattr(self._span, "end"):
            self._span.end()
