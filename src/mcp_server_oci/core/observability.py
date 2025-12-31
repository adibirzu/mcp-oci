"""
OCI Observability Integration - APM Tracing and Logging.

Provides unified observability using:
- OpenTelemetry SDK with OCI APM backend for distributed tracing
- Structured logging with OCI Logging service integration
- Performance monitoring and metrics

Environment Variables:
- OCI_APM_ENDPOINT: APM data upload endpoint
- OCI_APM_PRIVATE_DATA_KEY: APM private data key
- OCI_LOGGING_LOG_ID: Log OCID for ingestion
- OTEL_SDK_DISABLED: Disable tracing if 'true'
"""
from __future__ import annotations

import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

import structlog

# Global state
_tracer: Any | None = None
_logger: Any | None = None
_start_time: float = perf_counter()


def get_uptime_seconds() -> float:
    """Get server uptime in seconds."""
    return perf_counter() - _start_time


# ============================================================================
# Structured Logging with structlog
# ============================================================================

def configure_logging(
    level: str = "INFO",
    json_format: bool = False,
    service_name: str = "oci-mcp-server"
) -> None:
    """Configure structured logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: If True, output JSON; otherwise console format
        service_name: Service name for log context
    """
    # Configure processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        # Use stderr for MCP stdio compatibility (stdout is for JSON-RPC only)
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging to stderr
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,  # Must use stderr for MCP stdio transport
        level=getattr(logging, level.upper(), logging.INFO),
    )


def get_logger(name: str = "oci-mcp") -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# ============================================================================
# OpenTelemetry Tracing (Optional - requires otel dependencies)
# ============================================================================

def init_tracing(
    service_name: str = "oci-mcp-server",
    service_version: str = "2.0.0"
) -> Any | None:
    """Initialize OpenTelemetry tracing with OCI APM backend.

    This function attempts to initialize OTEL tracing. If the otel
    dependencies are not installed, it returns None gracefully.

    Args:
        service_name: Service name for traces
        service_version: Service version

    Returns:
        Tracer instance or None if disabled/unavailable
    """
    global _tracer

    # Check if disabled
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        get_logger().info("OpenTelemetry tracing disabled via OTEL_SDK_DISABLED")
        return None

    # Check for OCI APM configuration
    apm_endpoint = os.getenv("OCI_APM_ENDPOINT")
    apm_key = os.getenv("OCI_APM_PRIVATE_DATA_KEY")

    if not apm_endpoint or not apm_key:
        get_logger().info(
            "OCI APM not configured (missing OCI_APM_ENDPOINT or OCI_APM_PRIVATE_DATA_KEY)",
            hint="Tracing will be disabled"
        )
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Create resource with service info
        resource = Resource.create({
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            "cloud.provider": "oci",
            "cloud.region": os.getenv("OCI_REGION", "unknown"),
        })

        # Configure OTLP exporter for OCI APM
        otlp_exporter = OTLPSpanExporter(
            endpoint=f"{apm_endpoint}/20200101/opentelemetry/private/v1/traces",
            headers={"Authorization": f"dataKey {apm_key}"}
        )

        # Create and configure tracer provider
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer(service_name)

        get_logger().info(
            "OpenTelemetry tracing initialized",
            service=service_name,
            version=service_version,
            apm_endpoint=apm_endpoint[:30] + "..."
        )

        return _tracer

    except ImportError:
        get_logger().info(
            "OpenTelemetry packages not installed",
            hint="Install with: pip install opentelemetry-api "
                 "opentelemetry-sdk opentelemetry-exporter-otlp"
        )
        return None
    except Exception as e:
        get_logger().warning(
            "Failed to initialize OpenTelemetry",
            error=str(e)
        )
        return None


def get_tracer() -> Any | None:
    """Get the global tracer instance."""
    return _tracer


# ============================================================================
# Tool Execution Context
# ============================================================================

@dataclass
class ToolExecutionContext:
    """Context for tool execution with observability."""

    tool_name: str
    domain: str
    params: dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=perf_counter)
    span: Any | None = None
    logger: Any = None

    def __post_init__(self):
        if self.logger is None:
            self.logger = get_logger(f"oci-mcp.{self.domain}")

    @property
    def duration_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return (perf_counter() - self.start_time) * 1000

    def log_start(self) -> None:
        """Log tool execution start."""
        self.logger.info(
            f"Starting {self.tool_name}",
            tool=self.tool_name,
            domain=self.domain,
            params=_sanitize_params(self.params)
        )

    def log_success(self, result_summary: dict | None = None) -> None:
        """Log tool execution success."""
        self.logger.info(
            f"Completed {self.tool_name}",
            tool=self.tool_name,
            domain=self.domain,
            duration_ms=round(self.duration_ms, 2),
            **(result_summary or {})
        )

    def log_error(self, error: Exception) -> None:
        """Log tool execution error."""
        self.logger.error(
            f"Failed {self.tool_name}",
            tool=self.tool_name,
            domain=self.domain,
            duration_ms=round(self.duration_ms, 2),
            error_type=type(error).__name__,
            error_message=str(error)
        )


@asynccontextmanager
async def observe_tool(
    tool_name: str,
    domain: str,
    params: dict[str, Any] | None = None
) -> AsyncGenerator[None, None]:
    """Context manager for unified tool observability.

    Provides:
    - Structured logging (start, success, error)
    - Optional OTEL tracing if configured
    - Duration tracking

    Args:
        tool_name: Name of the tool being executed
        domain: Domain the tool belongs to
        params: Tool parameters (sensitive data will be masked)

    Yields:
        ToolExecutionContext with logging and timing utilities

    Example:
        async with observe_tool("oci_cost_get_summary", "cost", params) as ctx:
            result = await do_work()
            ctx.log_success({"items": len(result)})
    """
    ctx = ToolExecutionContext(
        tool_name=tool_name,
        domain=domain,
        params=params or {}
    )

    # Start tracing span if available
    tracer = get_tracer()
    if tracer:
        try:
            from opentelemetry import trace
            from opentelemetry.trace import Status, StatusCode

            ctx.span = tracer.start_span(
                tool_name,
                kind=trace.SpanKind.SERVER,
                attributes={
                    "tool.name": tool_name,
                    "tool.domain": domain,
                }
            )
        except ImportError:
            pass

    # Log start
    ctx.log_start()

    try:
        yield ctx

        # Log success
        ctx.log_success()

        # Mark span as successful
        if ctx.span:
            try:
                from opentelemetry.trace import Status, StatusCode
                ctx.span.set_status(Status(StatusCode.OK))
            except ImportError:
                pass

    except Exception as e:
        # Log error
        ctx.log_error(e)

        # Mark span as error
        if ctx.span:
            try:
                from opentelemetry.trace import Status, StatusCode
                ctx.span.record_exception(e)
                ctx.span.set_status(Status(StatusCode.ERROR, str(e)))
            except ImportError:
                pass

        raise

    finally:
        # End span
        if ctx.span:
            ctx.span.end()


# ============================================================================
# Utility Functions
# ============================================================================

def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    """Remove or mask sensitive data from parameters.

    Args:
        params: Original parameters

    Returns:
        Sanitized parameters safe for logging
    """
    sensitive_keys = {
        "password", "api_key", "private_key", "token",
        "secret", "credential", "auth"
    }

    sanitized = {}
    for key, value in params.items():
        # Check for sensitive keys
        if any(s in key.lower() for s in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        # Mask OCIDs (show first 20 and last 5 chars)
        elif key.endswith("_ocid") and isinstance(value, str) and len(value) > 30:
            sanitized[key] = f"{value[:20]}...{value[-5:]}"
        # Truncate long strings
        elif isinstance(value, str) and len(value) > 100:
            sanitized[key] = f"{value[:100]}..."
        else:
            sanitized[key] = value

    return sanitized


def mask_ocid(ocid: str) -> str:
    """Mask OCID for safe logging.

    Args:
        ocid: Full OCID string

    Returns:
        Masked OCID showing first 20 and last 5 chars
    """
    if len(ocid) > 30:
        return f"{ocid[:20]}...{ocid[-5:]}"
    return ocid


# ============================================================================
# Health Check Utilities
# ============================================================================

async def check_observability_health() -> dict[str, Any]:
    """Check health of observability components.

    Returns:
        Health status for tracing and logging
    """
    return {
        "tracing": {
            "enabled": _tracer is not None,
            "provider": "oci-apm" if _tracer else None
        },
        "logging": {
            "enabled": True,
            "provider": "structlog"
        },
        "uptime_seconds": round(get_uptime_seconds(), 2)
    }


# ============================================================================
# Module Initialization
# ============================================================================

def init_observability(
    service_name: str = "oci-mcp-server",
    service_version: str = "2.0.0",
    log_level: str = "INFO",
    json_logs: bool = False
) -> None:
    """Initialize all observability components.

    Args:
        service_name: Service name for tracing/logging
        service_version: Service version
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_logs: If True, output JSON logs
    """
    # Configure logging first
    configure_logging(
        level=log_level,
        json_format=json_logs,
        service_name=service_name
    )

    # Initialize tracing (optional)
    init_tracing(
        service_name=service_name,
        service_version=service_version
    )

    get_logger().info(
        "Observability initialized",
        service=service_name,
        version=service_version,
        log_level=log_level
    )
