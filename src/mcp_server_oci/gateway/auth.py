"""
MCP Gateway Authentication.

Provides OAuth 2.1 / Bearer token authentication for the gateway's
client-facing Streamable HTTP endpoint. Supports:

- JWT verification with RSA/EC public keys (production)
- Static token mapping (development/testing)
- Scope-based access control (global and per-tool)
- MCP OAuth 2.1 spec compliance (RFC 9728, RFC 8707)

The gateway acts as an OAuth Resource Server per the MCP 2025-06-18+
specification. Clients authenticate via Bearer tokens obtained from
an external Authorization Server.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from .config import GatewayAuthConfig

logger = structlog.get_logger("oci-mcp.gateway.auth")


@dataclass(frozen=True)
class TokenIdentity:
    """Represents an authenticated client identity from a validated token."""

    client_id: str
    scopes: list[str] = field(default_factory=list)
    subject: str | None = None
    issuer: str | None = None
    expires_at: float | None = None
    claims: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def has_scope(self, scope: str) -> bool:
        """Check if the identity has a specific scope."""
        return scope in self.scopes

    def has_all_scopes(self, scopes: list[str]) -> bool:
        """Check if the identity has all specified scopes."""
        return all(s in self.scopes for s in scopes)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthorizationError(Exception):
    """Raised when authorization fails (authenticated but insufficient permissions)."""

    def __init__(self, message: str, required_scopes: list[str] | None = None) -> None:
        super().__init__(message)
        self.required_scopes = required_scopes or []


class GatewayAuthProvider:
    """Authentication and authorization provider for the MCP Gateway.

    Validates incoming Bearer tokens and enforces scope-based access control.
    Supports JWT verification (production) and static tokens (development).
    """

    def __init__(self, config: GatewayAuthConfig) -> None:
        self._config = config
        self._public_key: str | None = None
        self._jwt_available = False

        # Load JWT public key if configured
        if config.jwt_public_key_file:
            try:
                with open(config.jwt_public_key_file) as f:
                    self._public_key = f.read()
                logger.info(
                    "JWT public key loaded",
                    key_file=config.jwt_public_key_file,
                )
            except FileNotFoundError:
                logger.warning(
                    "JWT public key file not found",
                    key_file=config.jwt_public_key_file,
                )

        # Check if PyJWT is available
        try:
            import jwt  # noqa: F401
            self._jwt_available = True
        except ImportError:
            if self._public_key:
                logger.warning(
                    "PyJWT not installed - JWT verification unavailable. "
                    "Install with: pip install PyJWT[crypto]"
                )

    @property
    def is_enabled(self) -> bool:
        """Whether authentication is enabled."""
        return self._config.enabled

    async def authenticate(self, token: str | None) -> TokenIdentity | None:
        """Authenticate an incoming request using the Bearer token.

        Args:
            token: Bearer token from the Authorization header (without 'Bearer ' prefix).
                   None if no Authorization header was present.

        Returns:
            TokenIdentity if authenticated, None if auth is disabled.

        Raises:
            AuthenticationError: If authentication fails.
        """
        if not self._config.enabled:
            return None

        if not token:
            raise AuthenticationError(
                "Authentication required. Provide a Bearer token in the Authorization header."
            )

        # Try static tokens first (development)
        identity = self._check_static_token(token)
        if identity:
            logger.debug("Authenticated via static token", client_id=identity.client_id)
            return identity

        # Try JWT verification (production)
        if self._public_key and self._jwt_available:
            identity = self._verify_jwt(token)
            if identity:
                logger.debug("Authenticated via JWT", client_id=identity.client_id)
                return identity

        raise AuthenticationError(
            "Invalid or expired token. Ensure the token is valid and not expired."
        )

    async def authorize_tool(self, identity: TokenIdentity | None, tool_name: str) -> None:
        """Check if the authenticated identity is authorized to call a tool.

        Args:
            identity: Authenticated identity (None if auth is disabled).
            tool_name: The tool being invoked.

        Raises:
            AuthorizationError: If the identity lacks required scopes.
        """
        if not self._config.enabled or identity is None:
            return

        # Check token expiration
        if identity.is_expired:
            raise AuthenticationError("Token has expired. Obtain a new token and retry.")

        # Check global required scopes
        if self._config.required_scopes:
            if not identity.has_all_scopes(self._config.required_scopes):
                missing = [s for s in self._config.required_scopes if not identity.has_scope(s)]
                raise AuthorizationError(
                    f"Insufficient scopes. Missing: {', '.join(missing)}",
                    required_scopes=missing,
                )

        # Check per-tool scopes
        tool_scopes = self._config.tool_scopes.get(tool_name, [])
        if tool_scopes and not identity.has_all_scopes(tool_scopes):
            missing = [s for s in tool_scopes if not identity.has_scope(s)]
            raise AuthorizationError(
                f"Tool '{tool_name}' requires additional scopes: {', '.join(missing)}",
                required_scopes=missing,
            )

    def _check_static_token(self, token: str) -> TokenIdentity | None:
        """Check token against static token mapping."""
        token_info = self._config.static_tokens.get(token)
        if token_info is None:
            return None

        return TokenIdentity(
            client_id=token_info.get("client_id", "unknown"),
            scopes=token_info.get("scopes", []),
            subject=token_info.get("subject"),
            issuer="static",
        )

    def _verify_jwt(self, token: str) -> TokenIdentity | None:
        """Verify a JWT token using the configured public key."""
        if not self._public_key:
            return None

        try:
            import jwt

            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=self._config.jwt_algorithms,
                issuer=self._config.jwt_issuer,
                audience=self._config.jwt_audience,
                options={
                    "require": ["exp", "iss", "sub"],
                    "verify_exp": True,
                    "verify_iss": bool(self._config.jwt_issuer),
                    "verify_aud": bool(self._config.jwt_audience),
                },
            )

            scope_claim = payload.get("scope")
            if isinstance(scope_claim, str):
                scopes = scope_claim.split()
            else:
                scopes = payload.get("scopes", [])

            raw_id = payload.get(
                "client_id", payload.get("azp", payload.get("sub", "unknown"))
            )
            return TokenIdentity(
                client_id=raw_id,
                scopes=scopes,
                subject=payload.get("sub"),
                issuer=payload.get("iss"),
                expires_at=payload.get("exp"),
                claims=payload,
            )

        except ImportError:
            logger.error("PyJWT not installed - cannot verify JWT tokens")
            return None
        except jwt.ExpiredSignatureError as e:
            raise AuthenticationError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            logger.debug("JWT verification failed", error=str(e))
            return None


def create_auth_provider(config: GatewayAuthConfig) -> GatewayAuthProvider:
    """Create an authentication provider from configuration.

    Args:
        config: Gateway authentication configuration.

    Returns:
        Configured GatewayAuthProvider instance.
    """
    return GatewayAuthProvider(config)
