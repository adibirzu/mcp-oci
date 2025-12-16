"""
OCI APM (Application Performance Monitoring) Integration

Provides OTEL tracing export to OCI APM, which uses HTTP/HTTPS with API key authentication
instead of the standard gRPC OTLP exporter.

Usage:
    from mcp_oci_common.oci_apm import init_oci_apm_tracing, get_apm_status

    # Initialize at startup
    tracer = init_oci_apm_tracing(service_name="oci-mcp-compute")

    # Check status
    status = get_apm_status()
    print(f"APM Enabled: {status['enabled']}")

Environment Variables:
    OCI_APM_ENDPOINT          - APM collector endpoint (required)
    OCI_APM_PRIVATE_DATA_KEY  - APM private data key for write access (required)
    OCI_APM_PUBLIC_DATA_KEY   - APM public data key (optional, for read-only dashboards)
    OTEL_SERVICE_NAME         - Service name (fallback if not provided)
    OTEL_TRACING_ENABLED      - Set to 'false' to disable tracing
"""

from __future__ import annotations

import os
import logging
import warnings
from typing import Optional, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# Module state
_apm_initialized = False
_apm_tracer = None
_apm_config: Dict[str, Any] = {}


def _get_oci_apm_config() -> Dict[str, Any]:
    """Get OCI APM configuration from environment variables."""
    return {
        "endpoint": os.getenv("OCI_APM_ENDPOINT"),
        "private_data_key": os.getenv("OCI_APM_PRIVATE_DATA_KEY"),
        "public_data_key": os.getenv("OCI_APM_PUBLIC_DATA_KEY"),
        "service_name": os.getenv("OTEL_SERVICE_NAME", "mcp-oci-server"),
        "service_version": os.getenv("SERVICE_VERSION", "1.0.0"),
        "enabled": os.getenv("OTEL_TRACING_ENABLED", "true").lower() == "true",
        "environment": os.getenv("DEPLOYMENT_ENVIRONMENT", os.getenv("ENVIRONMENT", "local")),
    }


def init_oci_apm_tracing(
    service_name: Optional[str] = None,
    *,
    service_version: Optional[str] = None,
    environment: Optional[str] = None,
) -> Optional[Any]:
    """
    Initialize OpenTelemetry tracing with OCI APM as the backend.

    OCI APM uses HTTP OTLP exporter with Authorization header containing the private data key.

    Args:
        service_name: Service name for tracing (defaults to OTEL_SERVICE_NAME env var)
        service_version: Service version (defaults to SERVICE_VERSION env var)
        environment: Deployment environment (defaults to DEPLOYMENT_ENVIRONMENT env var)

    Returns:
        Tracer instance if successful, None if disabled or failed

    Example:
        tracer = init_oci_apm_tracing(service_name="oci-mcp-compute")
        if tracer:
            with tracer.start_as_current_span("my_operation") as span:
                span.set_attribute("key", "value")
    """
    global _apm_initialized, _apm_tracer, _apm_config

    if _apm_initialized:
        return _apm_tracer

    config = _get_oci_apm_config()
    _apm_config = config

    # Check if enabled
    if not config["enabled"]:
        logger.info("OCI APM tracing disabled via OTEL_TRACING_ENABLED=false")
        _apm_initialized = True
        return None

    # Check required config
    if not config["endpoint"] or not config["private_data_key"]:
        logger.info(
            "OCI APM tracing disabled: OCI_APM_ENDPOINT and OCI_APM_PRIVATE_DATA_KEY required"
        )
        _apm_initialized = True
        return None

    # Try to import OpenTelemetry
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    except ImportError as e:
        warnings.warn(
            f"OpenTelemetry HTTP exporter not available: {e}. "
            "Install with: pip install opentelemetry-exporter-otlp-proto-http",
            UserWarning,
            stacklevel=2,
        )
        _apm_initialized = True
        return None

    # Build service name
    final_service_name = service_name or config["service_name"]
    final_service_version = service_version or config["service_version"]
    final_environment = environment or config["environment"]

    # Build resource attributes
    resource = Resource.create({
        SERVICE_NAME: final_service_name,
        SERVICE_VERSION: final_service_version,
        "deployment.environment": final_environment,
        "service.namespace": "oci-mcp",
    })

    # Configure OCI APM exporter
    # OCI APM expects Authorization header with the private data key
    headers = {
        "Authorization": f"dataKey {config['private_data_key']}",
    }

    try:
        # Create exporter with OCI APM endpoint
        exporter = OTLPSpanExporter(
            endpoint=config["endpoint"],
            headers=headers,
        )

        # Create and configure tracer provider
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        _apm_tracer = trace.get_tracer(final_service_name, final_service_version)
        _apm_initialized = True

        logger.info(
            f"OCI APM tracing initialized: service={final_service_name}, "
            f"version={final_service_version}, env={final_environment}"
        )

        return _apm_tracer

    except Exception as e:
        logger.error(f"Failed to initialize OCI APM tracing: {e}")
        _apm_initialized = True
        return None


def get_apm_tracer() -> Optional[Any]:
    """Get the APM tracer instance (initializes if not already done)."""
    global _apm_tracer
    if not _apm_initialized:
        init_oci_apm_tracing()
    return _apm_tracer


def get_apm_status() -> Dict[str, Any]:
    """Get OCI APM tracing status and configuration."""
    global _apm_initialized, _apm_tracer, _apm_config

    config = _apm_config if _apm_config else _get_oci_apm_config()

    return {
        "enabled": _apm_tracer is not None,
        "initialized": _apm_initialized,
        "service_name": config.get("service_name"),
        "service_version": config.get("service_version"),
        "environment": config.get("environment"),
        "endpoint": config.get("endpoint", "")[:50] + "..." if config.get("endpoint") else None,
        "has_private_key": bool(config.get("private_data_key")),
        "has_public_key": bool(config.get("public_data_key")),
    }


def send_test_span() -> Dict[str, Any]:
    """Send a test span to verify OCI APM connectivity."""
    tracer = get_apm_tracer()

    if not tracer:
        return {
            "success": False,
            "error": "APM tracer not initialized",
            "status": get_apm_status(),
        }

    try:
        with tracer.start_as_current_span("oci_apm_test_span") as span:
            span.set_attribute("test.type", "connectivity_check")
            span.set_attribute("test.source", "mcp_oci_common")
            span.add_event("test_event", {"message": "APM connectivity test"})

        return {
            "success": True,
            "message": "Test span sent successfully",
            "status": get_apm_status(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "status": get_apm_status(),
        }


def shutdown_apm():
    """Shutdown the APM tracer provider gracefully."""
    global _apm_initialized, _apm_tracer

    if not _apm_initialized or not _apm_tracer:
        return

    try:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()
        logger.info("OCI APM tracer shutdown complete")
    except Exception as e:
        logger.warning(f"Error during APM shutdown: {e}")
    finally:
        _apm_initialized = False
        _apm_tracer = None


# Convenience decorators
def trace_tool(tool_name: str, server_name: str = "oci-mcp"):
    """
    Decorator to trace MCP tool execution.

    Usage:
        @trace_tool("list_instances", "oci-mcp-compute")
        async def list_instances(compartment_id: str):
            ...
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            tracer = get_apm_tracer()
            if not tracer:
                return await func(*args, **kwargs)

            with tracer.start_as_current_span(f"mcp.tool.{tool_name}") as span:
                span.set_attribute("mcp.server.name", server_name)
                span.set_attribute("mcp.tool.name", tool_name)
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("mcp.tool.success", True)
                    return result
                except Exception as e:
                    span.set_attribute("mcp.tool.success", False)
                    span.set_attribute("mcp.tool.error", str(e))
                    span.record_exception(e)
                    raise

        def sync_wrapper(*args, **kwargs):
            tracer = get_apm_tracer()
            if not tracer:
                return func(*args, **kwargs)

            with tracer.start_as_current_span(f"mcp.tool.{tool_name}") as span:
                span.set_attribute("mcp.server.name", server_name)
                span.set_attribute("mcp.tool.name", tool_name)
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("mcp.tool.success", True)
                    return result
                except Exception as e:
                    span.set_attribute("mcp.tool.success", False)
                    span.set_attribute("mcp.tool.error", str(e))
                    span.record_exception(e)
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
