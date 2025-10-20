import os
from .config import get_oci_config, get_compartment_id, allow_mutations
from .observability import add_oci_call_attributes
from .validation import validate_and_log_tools

# Placeholder for with_oci_errors if needed
def with_oci_errors(func):
    return func


def make_client(oci_client_class, profile: str | None = None, region: str | None = None):
    """
    Factory for OCI SDK clients that supports both config-file auth and instance principals.

    Usage:
        from mcp_oci_common import make_client
        client = make_client(oci.log_analytics.LogAnalyticsClient, profile="DEFAULT", region="eu-frankfurt-1")
    """
    # Lazy import to avoid hard dependency at import time
    try:
        import oci as _oci  # type: ignore
    except Exception as _e:
        raise RuntimeError("OCI SDK not available. Please install 'oci' package.") from _e

    # Load config; supports instance principal fallback via get_oci_config()
    cfg = get_oci_config(profile_name=profile)
    if region:
        cfg["region"] = region

    signer = cfg.get("signer")
    if signer is not None:
        # Instance principals or other signer-based auth
        return oci_client_class(cfg, signer=signer)
    else:
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
            # Respect explicit parameters
            transport = kwargs.get("transport")
            if not transport:
                transport = os.getenv("MCP_TRANSPORT")
                if transport:
                    kwargs["transport"] = transport

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
                    server_name = os.getenv("FASTMCP_SERVER_NAME") or os.getenv("OTEL_SERVICE_NAME") or ""
                    port_map = {
                        "oci-mcp-compute": int(os.getenv("MCP_PORT_COMPUTE", "7001")),
                        "oci-mcp-db": int(os.getenv("MCP_PORT_DB", "7002")),
                        "oci-mcp-observability": int(os.getenv("MCP_PORT_OBSERVABILITY", "7003")),
                        "oci-mcp-security": int(os.getenv("MCP_PORT_SECURITY", "7004")),
                        "oci-mcp-cost": int(os.getenv("MCP_PORT_COST", "7005")),
                        "oci-mcp-network": int(os.getenv("MCP_PORT_NETWORK", "7006")),
                        "oci-mcp-blockstorage": int(os.getenv("MCP_PORT_BLOCKSTORAGE", "7007")),
                        "oci-mcp-loadbalancer": int(os.getenv("MCP_PORT_LOADBALANCER", "7008")),
                        "oci-mcp-inventory": int(os.getenv("MCP_PORT_INVENTORY", "7009")),
                        "oci-mcp-agents": int(os.getenv("MCP_PORT_AGENTS", "7011")),
                    }
                    port = port_map.get(server_name, int(os.getenv("MCP_PORT_DEFAULT", "7099")))
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
