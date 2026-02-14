"""
MCP Gateway - Aggregating proxy for multiple MCP servers.

Provides a single Streamable HTTP endpoint with OAuth/Bearer authentication
that routes tool calls to multiple backend MCP servers connected via
stdio, streamable HTTP, or in-process.
"""

from .config import (
    BackendAuthMethod,
    BackendConfig,
    BackendTransport,
    GatewayAuthConfig,
    GatewayConfig,
    load_gateway_config,
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
    # Registry
    "BackendRegistry",
    "BackendStatus",
    "BackendHealth",
    # Server
    "create_gateway",
    "run_gateway",
]
