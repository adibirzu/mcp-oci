"""
MCP Gateway Server.

The gateway aggregates multiple backend MCP servers (connected via stdio,
streamable HTTP, or in-process) into a single Streamable HTTP endpoint
with OAuth/Bearer authentication.

Architecture:
    Agent (OAuth Bearer) --> [Gateway :9000/mcp] --> Backend A (stdio, .oci/config)
                                                 --> Backend B (HTTP, resource principal)
                                                 --> Backend C (in-process)

Key features:
- FastMCP proxy-based tool aggregation with namespace prefixing
- OAuth 2.1 / Bearer token authentication (MCP 2025-06-18+ spec)
- Streamable HTTP transport with session management
- Backend health monitoring and graceful degradation
- Centralized audit logging for all tool invocations
- Per-tool scope-based access control
"""
from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastmcp import FastMCP

from .auth import GatewayAuthProvider, create_auth_provider
from .config import BackendConfig, BackendTransport, GatewayConfig, load_gateway_config
from .registry import BackendRegistry

logger = structlog.get_logger("oci-mcp.gateway")


@asynccontextmanager
async def gateway_lifespan(server: FastMCP) -> AsyncGenerator[dict[str, Any], None]:
    """Gateway lifespan manager.

    Initializes backend connections on startup and cleans up on shutdown.
    The registry and auth provider are stored in the lifespan context
    so gateway tools can access them.
    """
    config: GatewayConfig = server._gateway_config  # type: ignore[attr-defined]
    registry: BackendRegistry = server._gateway_registry  # type: ignore[attr-defined]
    auth_provider: GatewayAuthProvider = server._gateway_auth  # type: ignore[attr-defined]

    logger.info(
        "Starting MCP Gateway",
        name=config.name,
        version=config.version,
        backends=len(config.get_enabled_backends()),
        auth_enabled=config.auth.enabled,
    )

    # Register all backends
    for backend_config in config.get_enabled_backends():
        await registry.register(backend_config)

    # Connect to all backends
    results = await registry.connect_all()
    connected = sum(1 for v in results.values() if v)
    total = len(results)

    logger.info(
        "Backend connections established",
        connected=connected,
        total=total,
        failed=[name for name, ok in results.items() if not ok],
    )

    yield {
        "gateway_config": config,
        "registry": registry,
        "auth_provider": auth_provider,
    }

    # Shutdown
    logger.info("Shutting down MCP Gateway")
    await registry.disconnect_all()


def create_gateway(config: GatewayConfig | None = None) -> FastMCP:
    """Create and configure the MCP Gateway server.

    This builds a FastMCP server that acts as a proxy/aggregator for
    multiple backend MCP servers. It:

    1. Creates the gateway FastMCP instance with Streamable HTTP transport
    2. Registers backend configurations
    3. Mounts backend proxies with tool namespace prefixing
    4. Adds gateway-level management tools (health, backends, audit)
    5. Optionally configures Bearer token authentication

    Args:
        config: Gateway configuration. If None, loads from file/environment.

    Returns:
        Configured FastMCP gateway server ready to run.
    """
    if config is None:
        config = load_gateway_config()

    # Create registry and auth provider
    registry = BackendRegistry()
    auth_provider = create_auth_provider(config.auth)

    # Build FastMCP kwargs
    mcp_kwargs: dict[str, Any] = {
        "name": config.name,
        "instructions": _build_instructions(config),
    }

    # Configure auth if using JWT with a public key
    if config.auth.enabled and config.auth.jwt_public_key_file:
        try:
            from fastmcp.server.auth import BearerAuthProvider

            with open(config.auth.jwt_public_key_file) as f:
                public_key = f.read()

            mcp_kwargs["auth"] = BearerAuthProvider(
                public_key=public_key,
                issuer=config.auth.jwt_issuer,
                audience=config.auth.jwt_audience,
            )
            logger.info("FastMCP Bearer auth configured via JWT public key")
        except (ImportError, FileNotFoundError) as e:
            logger.warning(
                "FastMCP BearerAuthProvider not available, using custom auth",
                error=str(e),
            )

    if config.stateless:
        mcp_kwargs["stateless_http"] = True

    # Build the composite proxy from backend configs
    backends = config.get_enabled_backends()
    proxy_configs = _build_proxy_configs(backends)

    if proxy_configs:
        # Use FastMCP.as_proxy() for backend aggregation
        gateway = FastMCP.as_proxy(
            {"mcpServers": proxy_configs},
            **mcp_kwargs,
        )
    else:
        # No backends configured - create a standalone gateway
        gateway = FastMCP(**mcp_kwargs)

    # Attach config, registry, and auth to the server for lifespan access
    gateway._gateway_config = config  # type: ignore[attr-defined]
    gateway._gateway_registry = registry  # type: ignore[attr-defined]
    gateway._gateway_auth = auth_provider  # type: ignore[attr-defined]

    # Register gateway management tools
    _register_gateway_tools(gateway, config, registry, auth_provider)

    logger.info(
        "Gateway created",
        name=config.name,
        backends=len(backends),
        proxy_configs=len(proxy_configs),
        auth_enabled=config.auth.enabled,
    )

    return gateway


def _build_proxy_configs(backends: list[BackendConfig]) -> dict[str, Any]:
    """Convert backend configurations into FastMCP proxy format.

    Args:
        backends: List of enabled backend configurations.

    Returns:
        Dict mapping backend name to transport configuration.
    """
    configs: dict[str, Any] = {}

    for backend in backends:
        try:
            if backend.transport == BackendTransport.STDIO:
                if not backend.command:
                    logger.warning(
                        "Skipping stdio backend without command",
                        backend=backend.name,
                    )
                    continue

                proxy_cfg: dict[str, Any] = {
                    "command": backend.command,
                    "args": backend.args,
                    "env": backend.to_env_dict(),
                }
                if backend.cwd:
                    proxy_cfg["cwd"] = backend.cwd

                configs[backend.name] = proxy_cfg

            elif backend.transport == BackendTransport.STREAMABLE_HTTP:
                if not backend.url:
                    logger.warning(
                        "Skipping HTTP backend without URL",
                        backend=backend.name,
                    )
                    continue

                proxy_cfg = {
                    "url": backend.url,
                }
                if backend.bearer_token:
                    proxy_cfg["headers"] = {
                        "Authorization": f"Bearer {backend.bearer_token}",
                    }

                configs[backend.name] = proxy_cfg

            elif backend.transport == BackendTransport.IN_PROCESS:
                if not backend.module:
                    logger.warning(
                        "Skipping in-process backend without module",
                        backend=backend.name,
                    )
                    continue

                import importlib
                module = importlib.import_module(backend.module)
                server = getattr(module, backend.server_attr, None)
                if server is None:
                    logger.warning(
                        f"Module '{backend.module}' has no '{backend.server_attr}' attribute",
                        backend=backend.name,
                    )
                    continue

                configs[backend.name] = server

        except Exception as e:
            logger.error(
                "Failed to build proxy config for backend",
                backend=backend.name,
                error=str(e),
            )

    return configs


def _register_gateway_tools(
    gateway: FastMCP,
    config: GatewayConfig,
    registry: BackendRegistry,
    auth_provider: GatewayAuthProvider,
) -> None:
    """Register gateway-level management and observability tools.

    These tools provide visibility into the gateway itself, separate
    from the tools exposed by backend servers.
    """

    @gateway.tool(
        name="gateway_health",
        annotations={
            "title": "Gateway Health Check",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def gateway_health() -> str:
        """Check the health of the MCP Gateway and all connected backends.

        Returns server status, backend connection states, and overall health.
        """
        health = registry.get_health_summary()

        result = {
            "gateway": {
                "name": config.name,
                "version": config.version,
                "status": "healthy" if health["healthy"] > 0 else "degraded",
                "auth_enabled": config.auth.enabled,
            },
            "backends": health,
        }
        return json.dumps(result, indent=2, default=str)

    @gateway.tool(
        name="gateway_list_backends",
        annotations={
            "title": "List Gateway Backends",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def gateway_list_backends() -> str:
        """List all registered backend MCP servers and their status.

        Returns backend names, transport types, auth methods,
        health status, and available tool counts.
        """
        lines = ["# MCP Gateway Backends\n"]

        for name, entry in registry.backends.items():
            status_icon = {
                "healthy": "[OK]",
                "degraded": "[WARN]",
                "unhealthy": "[ERR]",
                "pending": "[...]",
                "connecting": "[...]",
                "disconnected": "[OFF]",
            }.get(entry.health.status.value, "[?]")

            lines.append(f"## {status_icon} {name}")
            lines.append(f"- **Transport:** {entry.config.transport.value}")
            lines.append(f"- **Auth:** {entry.config.auth_method.value}")
            lines.append(f"- **Status:** {entry.health.status.value}")
            if entry.health.latency_ms > 0:
                lines.append(f"- **Latency:** {entry.health.latency_ms:.1f}ms")
            if entry.health.error:
                lines.append(f"- **Error:** {entry.health.error}")
            lines.append(f"- **Tools:** {entry.health.tool_count}")
            lines.append("")

        if not registry.backends:
            lines.append("*No backends registered.*")

        return "\n".join(lines)

    @gateway.tool(
        name="gateway_audit_log",
        annotations={
            "title": "Gateway Audit Log",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def gateway_audit_log(limit: int = 20) -> str:
        """Get recent gateway audit log entries.

        Shows recent tool invocations with client identity, tool name,
        backend, and result status. Useful for monitoring and debugging.

        Args:
            limit: Maximum number of entries to return (1-100).
        """
        # The audit log is stored as a simple in-memory buffer
        # In production, this would be backed by OCI Logging or a database
        entries = _audit_buffer[-limit:] if _audit_buffer else []

        if not entries:
            return "No audit log entries found."

        lines = ["# Gateway Audit Log\n"]
        for entry in reversed(entries):
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry["timestamp"]))
            lines.append(
                f"- **{ts}** | `{entry['tool']}` | "
                f"client=`{entry.get('client_id', 'anonymous')}` | "
                f"backend=`{entry.get('backend', 'gateway')}` | "
                f"status=`{entry.get('status', 'unknown')}`"
            )

        return "\n".join(lines)


# Simple in-memory audit buffer (production would use OCI Logging)
_audit_buffer: list[dict[str, Any]] = []
_AUDIT_BUFFER_MAX = 1000


def record_audit_event(
    tool_name: str,
    client_id: str | None = None,
    backend: str | None = None,
    status: str = "success",
    details: dict[str, Any] | None = None,
) -> None:
    """Record an audit log entry for a tool invocation.

    Args:
        tool_name: Name of the tool that was called.
        client_id: Authenticated client identity.
        backend: Backend that handled the request.
        status: Result status (success, error, unauthorized).
        details: Additional details to log.
    """
    entry = {
        "timestamp": time.time(),
        "tool": tool_name,
        "client_id": client_id or "anonymous",
        "backend": backend or "gateway",
        "status": status,
    }
    if details:
        entry["details"] = details

    _audit_buffer.append(entry)

    # Trim buffer
    if len(_audit_buffer) > _AUDIT_BUFFER_MAX:
        del _audit_buffer[: len(_audit_buffer) - _AUDIT_BUFFER_MAX]

    logger.info(
        "audit",
        tool=tool_name,
        client_id=client_id,
        backend=backend,
        status=status,
    )


def _build_instructions(config: GatewayConfig) -> str:
    """Build gateway instructions string for MCP clients."""
    backend_names = [b.name for b in config.get_enabled_backends()]
    backend_list = ", ".join(backend_names) if backend_names else "none configured"

    return (
        f"MCP Gateway ({config.name} v{config.version}) aggregating tools from "
        f"multiple backend MCP servers: [{backend_list}].\n\n"
        "Use `gateway_health` to check overall gateway and backend health.\n"
        "Use `gateway_list_backends` to see registered backends and their status.\n"
        "Backend tools are namespaced as `backendname_toolname` to avoid collisions.\n"
    )


def run_gateway(config: GatewayConfig | None = None) -> None:
    """Create and run the MCP Gateway server.

    This is the main entry point for running the gateway. It creates
    the gateway, configures it, and starts the Streamable HTTP server.

    Args:
        config: Gateway configuration. If None, loads from file/environment.
    """
    if config is None:
        config = load_gateway_config()

    gateway = create_gateway(config)

    logger.info(
        "Starting MCP Gateway",
        host=config.host,
        port=config.port,
        path=config.path,
        auth_enabled=config.auth.enabled,
        backends=len(config.get_enabled_backends()),
    )

    gateway.run(
        transport="streamable-http",
        host=config.host,
        port=config.port,
        path=config.path,
    )
