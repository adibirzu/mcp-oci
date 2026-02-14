"""
MCP Gateway Configuration.

Defines configuration models for the gateway server, backend MCP servers,
authentication settings, and transport options. Configuration can be loaded
from a JSON/YAML file or constructed programmatically.

Environment Variables:
- MCP_GATEWAY_CONFIG: Path to gateway configuration file
- MCP_GATEWAY_HOST: Gateway listen address (default: 0.0.0.0)
- MCP_GATEWAY_PORT: Gateway listen port (default: 9000)
- MCP_GATEWAY_PATH: Gateway endpoint path (default: /mcp)
- MCP_GATEWAY_AUTH_ENABLED: Enable OAuth/Bearer auth (default: true)
- MCP_GATEWAY_JWT_PUBLIC_KEY: Path to JWT public key file
- MCP_GATEWAY_JWT_ISSUER: Expected JWT issuer
- MCP_GATEWAY_JWT_AUDIENCE: Expected JWT audience
- MCP_GATEWAY_LOG_LEVEL: Log level (default: INFO)
"""
from __future__ import annotations

import json
import os
from enum import StrEnum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BackendTransport(StrEnum):
    """Transport types for connecting to backend MCP servers."""
    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"
    IN_PROCESS = "in_process"


class BackendAuthMethod(StrEnum):
    """Authentication methods for backend MCP servers."""
    NONE = "none"
    OCI_CONFIG = "oci_config"
    RESOURCE_PRINCIPAL = "resource_principal"
    INSTANCE_PRINCIPAL = "instance_principal"
    BEARER_TOKEN = "bearer_token"
    API_KEY = "api_key"


class BackendConfig(BaseModel):
    """Configuration for a single backend MCP server."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    name: str = Field(
        ...,
        description="Unique identifier for this backend (used as tool namespace prefix)",
        min_length=1,
        max_length=64,
    )
    description: str = Field(
        default="",
        description="Human-readable description of what this backend provides",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this backend is active",
    )

    # Transport configuration
    transport: BackendTransport = Field(
        default=BackendTransport.STDIO,
        description="How the gateway connects to this backend",
    )

    # For stdio transport
    command: str | None = Field(
        default=None,
        description="Command to launch the backend process (stdio transport)",
    )
    args: list[str] = Field(
        default_factory=list,
        description="Command arguments (stdio transport)",
    )
    cwd: str | None = Field(
        default=None,
        description="Working directory for the backend process",
    )

    # For streamable_http transport
    url: str | None = Field(
        default=None,
        description="URL of the remote MCP server (streamable_http transport)",
    )

    # For in_process transport
    module: str | None = Field(
        default=None,
        description="Python module path for in-process server (e.g., mcp_server_oci.server)",
    )
    server_attr: str = Field(
        default="mcp",
        description="Attribute name of the FastMCP instance in the module",
    )

    # Environment variables passed to the backend
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set for the backend process",
    )

    # Authentication for this backend's OCI connections
    auth_method: BackendAuthMethod = Field(
        default=BackendAuthMethod.OCI_CONFIG,
        description="How this backend authenticates to OCI",
    )

    # OCI-specific configuration
    oci_profile: str | None = Field(
        default=None,
        description="OCI config profile name (for oci_config auth)",
    )
    oci_region: str | None = Field(
        default=None,
        description="OCI region override",
    )
    oci_config_file: str | None = Field(
        default=None,
        description="Path to OCI config file",
    )

    # Bearer token for remote backends
    bearer_token: str | None = Field(
        default=None,
        description="Bearer token for authenticating to remote backend (streamable_http)",
    )

    # Tool namespacing
    namespace_tools: bool = Field(
        default=True,
        description="Prefix tool names with backend name to avoid collisions",
    )

    # Health check
    health_check_interval: int = Field(
        default=30,
        description="Seconds between health checks (0 to disable)",
        ge=0,
    )

    # Timeouts
    connect_timeout: float = Field(
        default=10.0,
        description="Connection timeout in seconds",
    )
    request_timeout: float = Field(
        default=60.0,
        description="Request timeout in seconds",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is a valid identifier for namespacing."""
        if not v.replace("-", "_").replace(".", "_").isidentifier():
            msg = (
                f"Backend name '{v}' must be a valid identifier "
                "(letters, digits, hyphens, underscores)"
            )
            raise ValueError(msg)
        return v

    def to_env_dict(self) -> dict[str, str]:
        """Build environment dict for the backend process, including OCI auth."""
        env = dict(self.env)

        if self.auth_method == BackendAuthMethod.OCI_CONFIG:
            if self.oci_profile:
                env["OCI_PROFILE"] = self.oci_profile
            if self.oci_region:
                env["OCI_REGION"] = self.oci_region
            if self.oci_config_file:
                env["OCI_CONFIG_FILE"] = self.oci_config_file
        elif self.auth_method == BackendAuthMethod.RESOURCE_PRINCIPAL:
            env["OCI_CLI_AUTH"] = "resource_principal"
            if self.oci_region:
                env["OCI_REGION"] = self.oci_region
        elif self.auth_method == BackendAuthMethod.INSTANCE_PRINCIPAL:
            env["OCI_CLI_AUTH"] = "instance_principal"
            if self.oci_region:
                env["OCI_REGION"] = self.oci_region

        return env


class GatewayAuthConfig(BaseModel):
    """Authentication configuration for the gateway's client-facing endpoint."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    enabled: bool = Field(
        default=True,
        description="Enable OAuth/Bearer token authentication for incoming requests",
    )

    # JWT verification
    jwt_public_key_file: str | None = Field(
        default=None,
        description="Path to PEM-encoded RSA/EC public key for JWT verification",
    )
    jwt_issuer: str | None = Field(
        default=None,
        description="Expected JWT issuer (iss claim)",
    )
    jwt_audience: str | None = Field(
        default=None,
        description="Expected JWT audience (aud claim)",
    )
    jwt_algorithms: list[str] = Field(
        default_factory=lambda: ["RS256"],
        description="Allowed JWT signing algorithms",
    )

    # Static tokens (for development/testing)
    static_tokens: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Static token-to-identity mapping for development. "
            "Format: {token: {client_id: str, scopes: [str]}}"
        ),
    )

    # Scope-based access control
    required_scopes: list[str] = Field(
        default_factory=list,
        description="Scopes required for all gateway access",
    )

    # Per-tool access control
    tool_scopes: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Additional scopes required for specific tools: {tool_name: [scopes]}",
    )

    # CORS configuration
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins",
    )


class GatewayConfig(BaseModel):
    """Top-level configuration for the MCP Gateway."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    # Server settings
    name: str = Field(
        default="oci-mcp-gateway",
        description="Gateway server name",
    )
    version: str = Field(
        default="1.0.0",
        description="Gateway version",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Listen address",
    )
    port: int = Field(
        default=9000,
        description="Listen port",
        ge=1,
        le=65535,
    )
    path: str = Field(
        default="/mcp",
        description="MCP endpoint path",
    )
    log_level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR)",
    )

    # Stateless mode for horizontal scaling
    stateless: bool = Field(
        default=False,
        description="Run in stateless mode (no session affinity required)",
    )

    # Authentication
    auth: GatewayAuthConfig = Field(
        default_factory=GatewayAuthConfig,
        description="Client-facing authentication configuration",
    )

    # Backend MCP servers
    backends: list[BackendConfig] = Field(
        default_factory=list,
        description="List of backend MCP servers to aggregate",
    )

    # Observability
    enable_audit_log: bool = Field(
        default=True,
        description="Log all tool invocations with client identity",
    )
    enable_metrics: bool = Field(
        default=True,
        description="Enable gateway metrics collection",
    )

    def get_enabled_backends(self) -> list[BackendConfig]:
        """Return only enabled backend configurations."""
        return [b for b in self.backends if b.enabled]


def load_gateway_config(config_path: str | None = None) -> GatewayConfig:
    """Load gateway configuration from file and environment.

    Priority:
    1. Environment variables override file values
    2. Config file provides base configuration
    3. Defaults used for anything unspecified

    Args:
        config_path: Path to JSON config file. Falls back to
                     MCP_GATEWAY_CONFIG env var.

    Returns:
        Validated GatewayConfig instance
    """
    load_dotenv()

    path = config_path or os.getenv("MCP_GATEWAY_CONFIG")
    file_data: dict[str, Any] = {}

    if path and Path(path).exists():
        with open(path) as f:
            file_data = json.load(f)

    # Apply environment overrides
    env_overrides: dict[str, Any] = {}
    if os.getenv("MCP_GATEWAY_HOST"):
        env_overrides["host"] = os.getenv("MCP_GATEWAY_HOST")
    if os.getenv("MCP_GATEWAY_PORT"):
        env_overrides["port"] = int(os.getenv("MCP_GATEWAY_PORT", "9000"))
    if os.getenv("MCP_GATEWAY_PATH"):
        env_overrides["path"] = os.getenv("MCP_GATEWAY_PATH")
    if os.getenv("MCP_GATEWAY_LOG_LEVEL"):
        env_overrides["log_level"] = os.getenv("MCP_GATEWAY_LOG_LEVEL")
    if os.getenv("MCP_GATEWAY_NAME"):
        env_overrides["name"] = os.getenv("MCP_GATEWAY_NAME")

    # Auth overrides from environment
    if os.getenv("MCP_GATEWAY_AUTH_ENABLED") is not None:
        auth = file_data.get("auth", {})
        auth["enabled"] = os.getenv("MCP_GATEWAY_AUTH_ENABLED", "true").lower() == "true"

        if os.getenv("MCP_GATEWAY_JWT_PUBLIC_KEY"):
            auth["jwt_public_key_file"] = os.getenv("MCP_GATEWAY_JWT_PUBLIC_KEY")
        if os.getenv("MCP_GATEWAY_JWT_ISSUER"):
            auth["jwt_issuer"] = os.getenv("MCP_GATEWAY_JWT_ISSUER")
        if os.getenv("MCP_GATEWAY_JWT_AUDIENCE"):
            auth["jwt_audience"] = os.getenv("MCP_GATEWAY_JWT_AUDIENCE")

        env_overrides["auth"] = auth

    merged = {**file_data, **env_overrides}
    return GatewayConfig(**merged)
