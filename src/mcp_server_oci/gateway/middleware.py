"""
MCP Gateway guardrail middleware and composite token verifier.

Provides:
- CompositeTokenVerifier: FastMCP TokenVerifier that tries static tokens
  first, then JWT — bridges the existing GatewayAuthProvider into
  FastMCP's auth= constructor parameter.
- GatewayGuardrailMiddleware: MCP-layer middleware enforcing per-tool
  scope-based AuthZ, rate limiting, OTEL tracing, and audit logging.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

import structlog
from mcp import McpError
from mcp.types import ErrorData

from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.server.middleware.rate_limiting import SlidingWindowRateLimiter
from fastmcp.tools.tool import ToolResult

from .auth import GatewayAuthProvider
from .config import GatewayAuthConfig

logger = structlog.get_logger("oci-mcp.gateway.middleware")

# ── Tool classification ─────────────────────────────────────────────────────

_WRITE_VERBS = frozenset({
    "create", "delete", "stop", "terminate", "update", "modify",
    "patch", "remove", "drop", "kill", "start", "reboot",
    "remediate", "import", "clear", "disconnect",
})


def _is_write_tool(tool_name: str) -> bool:
    """Return True if any underscore-delimited segment is a write verb.

    Uses word-level matching (split on _) rather than substring to avoid
    misclassifying tools like 'list_started_instances' as write ops.
    """
    parts = set(tool_name.lower().split("_"))
    return bool(parts & _WRITE_VERBS)


# ── Composite Token Verifier ────────────────────────────────────────────────


class CompositeTokenVerifier(TokenVerifier):
    """FastMCP TokenVerifier that delegates to GatewayAuthProvider.

    Tries static token lookup first (O(1) dict), then JWT verification.
    Bridges the existing auth.py logic into FastMCP's HTTP-layer auth
    enforcement so that unauthenticated requests are rejected before
    reaching any MCP handler.
    """

    def __init__(self, gateway_auth: GatewayAuthProvider) -> None:
        super().__init__(
            required_scopes=list(gateway_auth._config.required_scopes)
            if gateway_auth._config.required_scopes
            else None,
        )
        self._gateway_auth = gateway_auth

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify via static map first, then JWT."""
        try:
            identity = await self._gateway_auth.authenticate(token)
        except Exception:
            return None

        if identity is None:
            return None

        return AccessToken(
            token=token,
            client_id=identity.client_id,
            scopes=identity.scopes,
            expires_at=int(identity.expires_at) if identity.expires_at else None,
            claims=dict(identity.claims),
        )


def create_composite_verifier(
    config: GatewayAuthConfig,
) -> CompositeTokenVerifier | None:
    """Build a CompositeTokenVerifier from gateway auth config.

    Returns None when auth is disabled so FastMCP skips token enforcement.

    Static tokens can be injected via MCP_GATEWAY_STATIC_TOKEN env var
    (avoids hardcoding tokens in ConfigMaps). Format: the raw token string.
    The env-injected token gets client_id="env-token" with read+write scopes.
    """
    import os

    if not config.enabled:
        return None

    # Inject static token from env var (Secret-backed in K8s)
    env_token = os.getenv("MCP_GATEWAY_STATIC_TOKEN", "")
    if env_token and env_token not in config.static_tokens:
        config.static_tokens[env_token] = {
            "client_id": "env-token",
            "scopes": ["read:tools", "write:tools"],
            "subject": "control-plane",
        }
        logger.info("static_token_injected_from_env")

    if not config.static_tokens and not config.jwt_public_key_file:
        logger.warning(
            "auth_enabled_but_no_credentials",
            hint="Set MCP_GATEWAY_STATIC_TOKEN env or jwt_public_key_file",
        )

    gateway_auth = GatewayAuthProvider(config)
    return CompositeTokenVerifier(gateway_auth)


# ── Guardrail Middleware ────────────────────────────────────────────────────


def _get_client_id_from_token() -> str:
    """Extract client_id from the current request's AccessToken."""
    token = get_access_token()
    return token.client_id if token else "anonymous"


class GatewayGuardrailMiddleware(Middleware):
    """MCP-layer middleware enforcing AuthZ, rate limits, tracing, and audit.

    Runs on every tools/call and:
    1. Reads the AccessToken injected by FastMCP's BearerAuthBackend.
    2. Enforces read:tools / write:tools scopes based on tool name.
    3. Applies per-client sliding-window rate limits.
    4. Creates OTEL spans per tool call (if tracer available).
    5. Records audit events for every invocation.
    """

    def __init__(
        self,
        auth_enabled: bool = True,
        general_limit: int = 100,
        write_limit: int = 10,
        window_seconds: int = 60,
    ) -> None:
        self._auth_enabled = auth_enabled
        self._general_limit = general_limit
        self._write_limit = write_limit
        self._window_seconds = window_seconds

        # Per-client sliding window limiters
        self._general_limiters: dict[str, SlidingWindowRateLimiter] = defaultdict(
            lambda: SlidingWindowRateLimiter(general_limit, window_seconds)
        )
        self._write_limiters: dict[str, SlidingWindowRateLimiter] = defaultdict(
            lambda: SlidingWindowRateLimiter(write_limit, window_seconds)
        )

        # OTEL tracer (lazy init)
        self._tracer = None
        self._call_counter = None
        self._latency_histogram = None
        self._init_otel()

    def _init_otel(self) -> None:
        """Try to get the OTEL tracer and metrics if already initialized."""
        try:
            from opentelemetry import trace, metrics

            tp = trace.get_tracer_provider()
            # Only use if a real provider is set (not the no-op default)
            if hasattr(tp, "get_tracer") and type(tp).__name__ != "ProxyTracerProvider":
                self._tracer = tp.get_tracer("oci-mcp-gateway.guardrail")

            mp = metrics.get_meter_provider()
            if type(mp).__name__ != "ProxyMeterProvider":
                meter = mp.get_meter("oci-mcp-gateway")
                self._call_counter = meter.create_counter(
                    "mcp.tool_calls",
                    description="Total MCP tool invocations",
                )
                self._latency_histogram = meter.create_histogram(
                    "mcp.tool_latency",
                    description="MCP tool call latency",
                    unit="ms",
                )
        except ImportError:
            pass

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: CallNext,
    ) -> ToolResult:
        tool_name: str = context.message.name
        write_op = _is_write_tool(tool_name)
        client_id = _get_client_id_from_token()
        t0 = time.monotonic()

        # ── 1. AuthZ: scope check ──────────────────────────────────────
        if self._auth_enabled:
            access_token = get_access_token()
            if access_token is None:
                # No token = unauthenticated. Reject at the MCP layer as a
                # defense-in-depth backstop even if the HTTP layer let it through.
                self._record(tool_name, client_id, "unauthorized")
                raise McpError(
                    ErrorData(code=-32001, message="Authentication required")
                )
            scopes = access_token.scopes or []
            required = "write:tools" if write_op else "read:tools"
            if required not in scopes:
                self._record(tool_name, client_id, "unauthorized")
                raise McpError(
                    ErrorData(
                        code=-32001,
                        message=f"Scope '{required}' required for '{tool_name}'",
                    )
                )

        # ── 2. Rate limit: general ─────────────────────────────────────
        limiter = self._general_limiters[client_id]
        if not await limiter.is_allowed():
            self._record(tool_name, client_id, "rate_limited")
            raise McpError(
                ErrorData(
                    code=-32000,
                    message=f"Rate limit exceeded: {self._general_limit}/{self._window_seconds}s",
                )
            )

        # ── 3. Rate limit: write-specific ──────────────────────────────
        if write_op:
            wl = self._write_limiters[client_id]
            if not await wl.is_allowed():
                self._record(tool_name, client_id, "rate_limited_write")
                raise McpError(
                    ErrorData(
                        code=-32000,
                        message=f"Write rate limit exceeded: {self._write_limit}/{self._window_seconds}s",
                    )
                )

        # ── 4. Execute with OTEL span ──────────────────────────────────
        if self._tracer:
            return await self._execute_with_span(
                context, call_next, tool_name, client_id, t0
            )

        # No tracer — execute without span
        try:
            result = await call_next(context)
            elapsed_ms = (time.monotonic() - t0) * 1000
            self._record_metrics(tool_name, client_id, elapsed_ms, "success")
            self._record(tool_name, client_id, "success")
            return result
        except Exception as exc:
            elapsed_ms = (time.monotonic() - t0) * 1000
            self._record_metrics(tool_name, client_id, elapsed_ms, "error")
            self._record(tool_name, client_id, "error", {"error": str(exc)[:200]})
            raise

    async def _execute_with_span(
        self,
        context: MiddlewareContext,
        call_next: CallNext,
        tool_name: str,
        client_id: str,
        t0: float,
    ) -> ToolResult:
        """Execute tool call inside an OTEL span (guaranteed end on exit)."""
        with self._tracer.start_as_current_span(
            "mcp.tool_call",
            attributes={
                "mcp.tool": tool_name,
                "mcp.client_id": client_id,
            },
        ) as span:
            try:
                result = await call_next(context)
                elapsed_ms = (time.monotonic() - t0) * 1000
                span.set_attribute("mcp.status", "success")
                span.set_attribute("mcp.latency_ms", round(elapsed_ms, 1))
                self._record_metrics(tool_name, client_id, elapsed_ms, "success")
                self._record(tool_name, client_id, "success")
                return result
            except Exception as exc:
                elapsed_ms = (time.monotonic() - t0) * 1000
                span.set_attribute("mcp.status", "error")
                span.set_attribute("mcp.error", str(exc)[:200])
                self._record_metrics(tool_name, client_id, elapsed_ms, "error")
                self._record(tool_name, client_id, "error", {"error": str(exc)[:200]})
                raise

    def _record_metrics(
        self, tool: str, client: str, latency_ms: float, status: str
    ) -> None:
        """Record OTEL metrics for a tool call."""
        attrs = {"mcp.tool": tool, "mcp.client_id": client, "mcp.status": status}
        if self._call_counter:
            self._call_counter.add(1, attrs)
        if self._latency_histogram:
            self._latency_histogram.record(latency_ms, attrs)

    def _record(
        self,
        tool_name: str,
        client_id: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record audit event (late import to avoid circular dependency)."""
        try:
            from .server import record_audit_event  # noqa: PLC0415

            record_audit_event(
                tool_name, client_id=client_id, status=status, details=details
            )
        except ImportError:
            pass
