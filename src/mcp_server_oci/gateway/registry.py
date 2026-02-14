"""
Backend Server Registry.

Manages the lifecycle of backend MCP servers connected to the gateway.
Handles:

- Backend discovery and connection (stdio, streamable HTTP, in-process)
- Health monitoring with automatic quarantine/recovery
- Tool catalog aggregation with namespace prefixing
- Environment propagation for OCI authentication
"""
from __future__ import annotations

import asyncio
import contextlib
import importlib
import os
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

from .config import BackendConfig, BackendTransport

logger = structlog.get_logger("oci-mcp.gateway.registry")


class BackendStatus(StrEnum):
    """Lifecycle states for a backend server."""
    PENDING = "pending"
    CONNECTING = "connecting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISCONNECTED = "disconnected"


@dataclass
class BackendHealth:
    """Health information for a backend server."""
    status: BackendStatus = BackendStatus.PENDING
    last_check: float = 0.0
    last_healthy: float = 0.0
    consecutive_failures: int = 0
    error: str | None = None
    tool_count: int = 0
    latency_ms: float = 0.0

    @property
    def seconds_since_check(self) -> float:
        if self.last_check == 0:
            return float("inf")
        return time.time() - self.last_check

    @property
    def seconds_since_healthy(self) -> float:
        if self.last_healthy == 0:
            return float("inf")
        return time.time() - self.last_healthy


@dataclass
class BackendEntry:
    """A registered backend with its configuration, connection, and health."""
    config: BackendConfig
    health: BackendHealth = field(default_factory=BackendHealth)
    proxy_server: Any | None = None  # FastMCP proxy instance
    tool_names: list[str] = field(default_factory=list)

    @property
    def is_available(self) -> bool:
        return self.health.status in (BackendStatus.HEALTHY, BackendStatus.DEGRADED)


class BackendRegistry:
    """Registry managing all backend MCP server connections.

    The registry handles connecting to backends, monitoring their health,
    and providing a unified view of available tools across all backends.
    """

    def __init__(self) -> None:
        self._backends: dict[str, BackendEntry] = {}
        self._health_tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    @property
    def backends(self) -> dict[str, BackendEntry]:
        return dict(self._backends)

    @property
    def healthy_backends(self) -> dict[str, BackendEntry]:
        return {k: v for k, v in self._backends.items() if v.is_available}

    async def register(self, config: BackendConfig) -> None:
        """Register a backend server configuration.

        Args:
            config: Backend configuration to register.
        """
        async with self._lock:
            if config.name in self._backends:
                logger.warning("Backend already registered, replacing", backend=config.name)
                await self._disconnect_backend(config.name)

            self._backends[config.name] = BackendEntry(config=config)
            logger.info(
                "Backend registered",
                backend=config.name,
                transport=config.transport.value,
                auth=config.auth_method.value,
            )

    async def connect_all(self) -> dict[str, bool]:
        """Connect to all registered backends.

        Returns:
            Dict mapping backend name to connection success.
        """
        results: dict[str, bool] = {}
        tasks = []

        for name in list(self._backends.keys()):
            tasks.append(self._connect_backend(name))

        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        for name, outcome in zip(self._backends.keys(), outcomes, strict=False):
            if isinstance(outcome, Exception):
                logger.error("Failed to connect backend", backend=name, error=str(outcome))
                results[name] = False
            else:
                results[name] = outcome

        return results

    async def _connect_backend(self, name: str) -> bool:
        """Connect to a single backend server.

        Args:
            name: Backend name.

        Returns:
            True if connection succeeded.
        """
        entry = self._backends.get(name)
        if not entry:
            return False

        config = entry.config
        entry.health.status = BackendStatus.CONNECTING

        try:
            proxy = await self._create_proxy(config)
            entry.proxy_server = proxy
            entry.health.status = BackendStatus.HEALTHY
            entry.health.last_healthy = time.time()
            entry.health.last_check = time.time()
            entry.health.consecutive_failures = 0

            logger.info(
                "Backend connected",
                backend=name,
                transport=config.transport.value,
            )

            # Start health check loop if configured
            if config.health_check_interval > 0:
                task = asyncio.create_task(
                    self._health_check_loop(name, config.health_check_interval)
                )
                self._health_tasks[name] = task

            return True

        except Exception as e:
            entry.health.status = BackendStatus.UNHEALTHY
            entry.health.error = str(e)
            entry.health.last_check = time.time()
            logger.error("Backend connection failed", backend=name, error=str(e))
            return False

    async def _create_proxy(self, config: BackendConfig) -> Any:
        """Create a FastMCP proxy for the given backend configuration.

        Returns a proxy server configuration dict compatible with
        FastMCP.as_proxy() for later aggregation.
        """
        if config.transport == BackendTransport.STDIO:
            return self._build_stdio_config(config)
        elif config.transport == BackendTransport.STREAMABLE_HTTP:
            return self._build_http_config(config)
        elif config.transport == BackendTransport.IN_PROCESS:
            return await self._build_in_process_config(config)
        else:
            msg = f"Unsupported transport: {config.transport}"
            raise ValueError(msg)

    def _build_stdio_config(self, config: BackendConfig) -> dict[str, Any]:
        """Build a stdio transport configuration for FastMCP proxy."""
        if not config.command:
            msg = f"Backend '{config.name}': stdio transport requires 'command'"
            raise ValueError(msg)

        # Merge environment: inherit current env + backend-specific env + OCI auth env
        env = {**os.environ, **config.to_env_dict()}

        proxy_config: dict[str, Any] = {
            "command": config.command,
            "args": config.args,
            "env": env,
            "transport": "stdio",
        }

        if config.cwd:
            proxy_config["cwd"] = config.cwd

        return proxy_config

    def _build_http_config(self, config: BackendConfig) -> dict[str, Any]:
        """Build a streamable HTTP transport configuration."""
        if not config.url:
            msg = f"Backend '{config.name}': streamable_http transport requires 'url'"
            raise ValueError(msg)

        proxy_config: dict[str, Any] = {
            "url": config.url,
            "transport": "http",
        }

        if config.bearer_token:
            proxy_config["headers"] = {
                "Authorization": f"Bearer {config.bearer_token}",
            }

        return proxy_config

    async def _build_in_process_config(self, config: BackendConfig) -> Any:
        """Build an in-process server reference.

        Imports the Python module and returns the FastMCP server instance.
        """
        if not config.module:
            msg = f"Backend '{config.name}': in_process transport requires 'module'"
            raise ValueError(msg)

        try:
            module = importlib.import_module(config.module)
            server = getattr(module, config.server_attr, None)
            if server is None:
                msg = (
                    f"Module '{config.module}' has no attribute '{config.server_attr}'. "
                    f"Set 'server_attr' to the FastMCP instance name."
                )
                raise AttributeError(msg)
            return server
        except ImportError as e:
            msg = f"Cannot import module '{config.module}': {e}"
            raise ImportError(msg) from e

    async def _health_check_loop(self, name: str, interval: int) -> None:
        """Background health check loop for a backend."""
        while True:
            await asyncio.sleep(interval)

            entry = self._backends.get(name)
            if not entry:
                break

            try:
                start = time.time()
                healthy = await self._check_backend_health(entry)
                latency = (time.time() - start) * 1000

                entry.health.last_check = time.time()
                entry.health.latency_ms = latency

                if healthy:
                    entry.health.status = BackendStatus.HEALTHY
                    entry.health.last_healthy = time.time()
                    entry.health.consecutive_failures = 0
                    entry.health.error = None
                else:
                    entry.health.consecutive_failures += 1
                    if entry.health.consecutive_failures >= 3:
                        entry.health.status = BackendStatus.UNHEALTHY
                    else:
                        entry.health.status = BackendStatus.DEGRADED

            except asyncio.CancelledError:
                break
            except Exception as e:
                entry.health.consecutive_failures += 1
                entry.health.error = str(e)
                entry.health.last_check = time.time()
                if entry.health.consecutive_failures >= 3:
                    entry.health.status = BackendStatus.UNHEALTHY
                else:
                    entry.health.status = BackendStatus.DEGRADED

                logger.warning(
                    "Health check failed",
                    backend=name,
                    failures=entry.health.consecutive_failures,
                    error=str(e),
                )

    async def _check_backend_health(self, entry: BackendEntry) -> bool:
        """Perform a health check on a backend.

        For stdio backends, we check if the process config is still valid.
        For HTTP backends, we attempt a lightweight request.
        For in-process backends, we check if the server object is accessible.

        Returns:
            True if the backend is healthy.
        """
        config = entry.config

        if config.transport == BackendTransport.IN_PROCESS:
            return entry.proxy_server is not None

        if config.transport == BackendTransport.STREAMABLE_HTTP:
            if not config.url:
                return False
            try:
                import httpx
                headers = {}
                if config.bearer_token:
                    headers["Authorization"] = f"Bearer {config.bearer_token}"
                async with httpx.AsyncClient(timeout=config.connect_timeout) as client:
                    response = await client.get(
                        config.url,
                        headers={**headers, "Accept": "text/event-stream"},
                    )
                    # Streamable HTTP servers may return various codes for GET
                    # A 200 or 405 means the server is responding
                    return response.status_code in (200, 405, 406)
            except Exception:
                return False

        if config.transport == BackendTransport.STDIO:
            # For stdio, we trust the config is valid if the command exists
            return entry.proxy_server is not None

        return False

    async def _disconnect_backend(self, name: str) -> None:
        """Disconnect and clean up a backend."""
        # Cancel health check task
        task = self._health_tasks.pop(name, None)
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        entry = self._backends.pop(name, None)
        if entry:
            entry.health.status = BackendStatus.DISCONNECTED
            entry.proxy_server = None
            logger.info("Backend disconnected", backend=name)

    async def disconnect_all(self) -> None:
        """Disconnect all backends and cancel health checks."""
        names = list(self._backends.keys())
        for name in names:
            await self._disconnect_backend(name)

    def get_health_summary(self) -> dict[str, Any]:
        """Get a summary of all backend health states.

        Returns:
            Health summary with per-backend status.
        """
        entries = self._backends.values()
        summary: dict[str, Any] = {
            "total": len(self._backends),
            "healthy": sum(
                1 for e in entries if e.health.status == BackendStatus.HEALTHY
            ),
            "degraded": sum(
                1 for e in entries if e.health.status == BackendStatus.DEGRADED
            ),
            "unhealthy": sum(
                1 for e in entries if e.health.status == BackendStatus.UNHEALTHY
            ),
            "backends": {},
        }

        for name, entry in self._backends.items():
            summary["backends"][name] = {
                "status": entry.health.status.value,
                "transport": entry.config.transport.value,
                "auth_method": entry.config.auth_method.value,
                "tool_count": entry.health.tool_count,
                "latency_ms": round(entry.health.latency_ms, 2),
                "last_check": entry.health.last_check,
                "consecutive_failures": entry.health.consecutive_failures,
                "error": entry.health.error,
            }

        return summary

    def build_proxy_config(self) -> dict[str, dict[str, Any]]:
        """Build a unified proxy configuration for FastMCP.as_proxy().

        Converts all healthy backend entries into the format expected by
        FastMCP's composite proxy system.

        Returns:
            Dict in FastMCP mcpServers format:
            {"mcpServers": {name: {transport_config}}}
        """
        servers: dict[str, Any] = {}

        for name, entry in self._backends.items():
            if not entry.is_available:
                logger.debug("Skipping unavailable backend", backend=name)
                continue

            proxy = entry.proxy_server
            if proxy is None:
                continue

            if isinstance(proxy, dict):
                # stdio or http config dict
                servers[name] = proxy
            else:
                # In-process FastMCP server object - store directly
                servers[name] = proxy

        return {"mcpServers": servers}
