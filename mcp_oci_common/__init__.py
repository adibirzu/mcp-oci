import os
from .config import (
    get_oci_config,
    get_compartment_id,
    allow_mutations,
)
from .observability import add_oci_call_attributes
from .validation import validate_and_log_tools

# OCI APM (Application Performance Monitoring) integration
try:
    from .oci_apm import (
        init_oci_apm_tracing,
        get_apm_tracer,
        get_apm_status,
        send_test_span,
        shutdown_apm,
        trace_tool,
    )
    _OCI_APM_AVAILABLE = True
except ImportError:
    _OCI_APM_AVAILABLE = False

# Smart resolver imports (optional, won't break if not available)
try:
    from .smart_resolver import (
        resolve_compartment,
        get_compartment_info,
        search_compartments,
        list_all_compartments,
        get_resolver,
        smart_compartment_id,
        smart_time_range,
        smart_time_range_iso,
        CompartmentResolver,
        CompartmentInfo,
    )
    _SMART_RESOLVER_AVAILABLE = True
except ImportError:
    _SMART_RESOLVER_AVAILABLE = False

__all__ = [
    "get_oci_config",
    "get_compartment_id",
    "allow_mutations",
    "add_oci_call_attributes",
    "validate_and_log_tools",
    "with_oci_errors",
    "make_client",
    # Smart resolver exports
    "resolve_compartment",
    "get_compartment_info",
    "search_compartments",
    "list_all_compartments",
    "get_resolver",
    "smart_compartment_id",
    "smart_time_range",
    "smart_time_range_iso",
    "CompartmentResolver",
    "CompartmentInfo",
    # OCI APM exports
    "init_oci_apm_tracing",
    "get_apm_tracer",
    "get_apm_status",
    "send_test_span",
    "shutdown_apm",
    "trace_tool",
]


# Placeholder for with_oci_errors if needed
def with_oci_errors(func):
    return func


def make_client(
    oci_client_class, profile: str | None = None, region: str | None = None
):
    """
    Factory for OCI SDK clients that supports both config-file auth and instance principals.

    Usage:
        from mcp_oci_common import make_client
        client = make_client(oci.log_analytics.LogAnalyticsClient, profile="DEFAULT", region="eu-frankfurt-1")
    """
    # Prefer the shared cached factory (adds retries/timeouts and reuses clients)
    try:
        from .session import get_client as _get_client

        return _get_client(oci_client_class, profile=profile, region=region)
    except Exception:
        # Fallback to legacy behavior if session module or kwargs not supported
        import importlib.util as _importlib

        if _importlib.find_spec("oci") is None:
            raise RuntimeError("OCI SDK not available. Please install 'oci' package.")
        cfg = get_oci_config(profile_name=profile)
        if region:
            cfg["region"] = region
        signer = cfg.get("signer")
        try:
            if signer is not None:
                return oci_client_class(cfg, signer=signer)
            else:
                return oci_client_class(cfg)
        except TypeError:
            # Safety if client signature mismatch
            if signer is not None:
                return oci_client_class(cfg, signer=signer)
            return oci_client_class(cfg)


# --- Global FastMCP run() defaults/monkey-patch for network transport ---
# This enables running servers over network (e.g., WebSocket) without modifying each server.
# Behavior:
# - If MCP_TRANSPORT=ws/http and no transport explicitly passed, run() uses that transport
# - host defaults to MCP_HOST or 0.0.0.0
# - port defaults per-server name (FASTMCP_SERVER_NAME) to avoid clashes when many servers run in one container
#   You can override via MCP_PORT or specific MCP_PORT_<SERVICE> envs (see port_map below)
try:
    from fastmcp import FastMCP as _FastMCP  # type: ignore

    _orig_run = getattr(_FastMCP, "run", None)
    if callable(_orig_run):

        def _patched_run(self, *args, **kwargs):
            # Respect explicit parameters; only accept known transports from env
            transport = kwargs.get("transport")
            if not transport:
                env_transport = os.getenv("MCP_TRANSPORT")
                valid_transports = {"stdio", "http", "sse", "streamable-http"}
                # Ignore invalid values like "all" to avoid crashes under Claude/clients
                if env_transport in valid_transports:
                    kwargs["transport"] = env_transport

            if kwargs.get("transport") and kwargs["transport"] != "stdio":
                # Network mode: set sane defaults
                kwargs.setdefault("host", os.getenv("MCP_HOST", "0.0.0.0"))
                # Derive port
                port_env = os.getenv("MCP_PORT")
                if port_env:
                    try:
                        port = int(port_env)
                    except Exception:
                        port = None
                else:
                    server_name = (
                        os.getenv("FASTMCP_SERVER_NAME")
                        or os.getenv("OTEL_SERVICE_NAME")
                        or ""
                    )
                    port_map = {
                        "oci-mcp-compute": int(os.getenv("MCP_PORT_COMPUTE", "7001")),
                        "oci-mcp-db": int(os.getenv("MCP_PORT_DB", "7002")),
                        "oci-mcp-observability": int(
                            os.getenv("MCP_PORT_OBSERVABILITY", "7003")
                        ),
                        "oci-mcp-security": int(os.getenv("MCP_PORT_SECURITY", "7004")),
                        "oci-mcp-cost": int(os.getenv("MCP_PORT_COST", "7005")),
                        "oci-mcp-network": int(os.getenv("MCP_PORT_NETWORK", "7006")),
                        "oci-mcp-blockstorage": int(
                            os.getenv("MCP_PORT_BLOCKSTORAGE", "7007")
                        ),
                        "oci-mcp-loadbalancer": int(
                            os.getenv("MCP_PORT_LOADBALANCER", "7008")
                        ),
                        "oci-mcp-inventory": int(
                            os.getenv("MCP_PORT_INVENTORY", "7009")
                        ),
                        "oci-mcp-agents": int(os.getenv("MCP_PORT_AGENTS", "7011")),
                    }
                    port = port_map.get(
                        server_name, int(os.getenv("MCP_PORT_DEFAULT", "7099"))
                    )
                if port is not None:
                    kwargs.setdefault("port", port)

                # Avoid accidental conflict if Prometheus metrics are using same port
                try:
                    mp = os.getenv("METRICS_PORT")
                    if mp and int(mp) == kwargs.get("port"):
                        os.environ["METRICS_PORT"] = "-1"  # disable metrics exporter
                except Exception:
                    pass

            return _orig_run(self, *args, **kwargs)

        setattr(_FastMCP, "run", _patched_run)
except Exception:
    # If FastMCP is not installed at import time, skip silently
    pass
