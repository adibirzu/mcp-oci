"""
MCP Gateway - Aggregating proxy for multiple MCP servers.

Provides a single Streamable HTTP endpoint with OAuth/Bearer authentication
that routes tool calls to multiple backend MCP servers connected via
stdio, streamable HTTP, or in-process.

Supports auto-discovery of MCP servers from external projects, directories,
and .mcp.json configuration files.
"""

from .config import (
    BackendAuthMethod,
    BackendConfig,
    BackendTransport,
    GatewayAuthConfig,
    GatewayConfig,
    load_gateway_config,
)
from .discovery import (
    discover_backends,
    discover_from_mcp_json,
    load_backends_dir,
)
from .registry import BackendHealth, BackendRegistry, BackendStatus
from .server import create_gateway, run_gateway

__all__ = [
    # Config
    "GatewayConfig",
    "GatewayAuthConfig",
    "BackendConfig",
    "BackendTransport",
    "BackendAuthMethod",
    "load_gateway_config",
    # Discovery
    "discover_backends",
    "discover_from_mcp_json",
    "load_backends_dir",
    # Registry
    "BackendRegistry",
    "BackendStatus",
    "BackendHealth",
    # Server
    "create_gateway",
    "run_gateway",
]
