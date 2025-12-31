"""
OCI MCP Server Configuration

Handles environment variables, OCI config, and server settings.
All sensitive values are sourced from environment variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class AuthMethod(str, Enum):
    """OCI Authentication methods."""
    CONFIG_FILE = "config_file"
    INSTANCE_PRINCIPAL = "instance_principal"
    RESOURCE_PRINCIPAL = "resource_principal"
    API_KEY = "api_key"


class TransportType(str, Enum):
    """MCP transport types."""
    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"


class ServerConfig(BaseModel):
    """MCP Server configuration."""
    name: str = Field(default="oci-mcp", description="Server name")
    version: str = Field(default="2.0.0", description="Server version")
    transport: TransportType = Field(
        default=TransportType.STDIO,
        description="Transport: stdio or streamable_http"
    )
    port: int = Field(default=8000, description="HTTP port if using streamable_http")
    log_level: str = Field(default="INFO", description="Logging level")
    enable_metrics: bool = Field(default=True, description="Enable telemetry")
    allow_mutations: bool = Field(default=False, description="Allow write operations")


class OCIConfig(BaseModel):
    """OCI SDK configuration."""
    auth_method: AuthMethod = Field(
        default=AuthMethod.CONFIG_FILE,
        description="Authentication method"
    )
    config_file: Path = Field(
        default=Path("~/.oci/config").expanduser(),
        description="OCI config file path"
    )
    profile: str = Field(default="DEFAULT", description="OCI config profile")
    tenancy_ocid: str | None = Field(default=None, description="Override tenancy OCID")
    region: str | None = Field(default=None, description="Override region")
    compartment_ocid: str | None = Field(default=None, description="Default compartment OCID")

    # Rate limiting
    max_retries: int = Field(default=3, description="Max API retries")
    retry_delay: float = Field(default=1.0, description="Retry delay in seconds")

    @field_validator('config_file', mode='before')
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        return Path(v).expanduser()


class APMConfig(BaseModel):
    """OCI APM (Application Performance Monitoring) configuration."""
    enabled: bool = Field(default=False, description="Enable OCI APM tracing")
    endpoint: str | None = Field(default=None, description="APM data upload endpoint")
    private_data_key: str | None = Field(default=None, description="APM private data key")
    domain_id: str | None = Field(default=None, description="APM domain OCID")
    service_name: str = Field(default="oci-mcp-server", description="Service name for traces")


class LoggingConfig(BaseModel):
    """OCI Logging configuration."""
    enabled: bool = Field(default=False, description="Enable OCI Logging integration")
    log_id: str | None = Field(default=None, description="Log OCID for ingestion")
    compartment_id: str | None = Field(default=None, description="Compartment for logging")
    batch_size: int = Field(default=100, description="Log batch size before flush")
    flush_interval: float = Field(default=5.0, description="Flush interval in seconds")


class LogAnalyticsConfig(BaseModel):
    """OCI Log Analytics configuration."""
    enabled: bool = Field(default=False, description="Enable Log Analytics upload")
    namespace: str | None = Field(default=None, description="Log Analytics namespace")
    log_group_id: str | None = Field(default=None, description="Log group OCID")
    source_name: str = Field(default="oci-mcp-server", description="Log source name")
    entity_id: str | None = Field(default=None, description="Entity OCID (optional)")


class ObservabilityConfig(BaseModel):
    """Combined observability configuration."""
    apm: APMConfig = Field(default_factory=APMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    log_analytics: LogAnalyticsConfig = Field(default_factory=LogAnalyticsConfig)


@dataclass
class AppConfig:
    """Application configuration container."""
    server: ServerConfig = field(default_factory=ServerConfig)
    oci: OCIConfig = field(default_factory=OCIConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load configuration from environment variables.

        Environment variables referenced:
        - [Link to Secure Variable: OCI_MCP_NAME]
        - [Link to Secure Variable: OCI_MCP_TRANSPORT]
        - [Link to Secure Variable: OCI_MCP_PORT]
        - [Link to Secure Variable: OCI_MCP_LOG_LEVEL]
        - [Link to Secure Variable: ALLOW_MUTATIONS]
        - [Link to Secure Variable: OCI_AUTH_METHOD]
        - [Link to Secure Variable: OCI_CONFIG_FILE]
        - [Link to Secure Variable: OCI_PROFILE]
        - [Link to Secure Variable: OCI_TENANCY_OCID]
        - [Link to Secure Variable: OCI_REGION]
        - [Link to Secure Variable: COMPARTMENT_OCID]
        - [Link to Secure Variable: OCI_APM_ENDPOINT]
        - [Link to Secure Variable: OCI_APM_PRIVATE_DATA_KEY]
        - [Link to Secure Variable: OCI_APM_DOMAIN_ID]
        - [Link to Secure Variable: OCI_LOGGING_LOG_ID]
        - [Link to Secure Variable: OCI_LOGAN_NAMESPACE]
        - [Link to Secure Variable: OCI_LOGAN_LOG_GROUP_ID]
        """
        load_dotenv()

        return cls(
            server=ServerConfig(
                name=os.getenv("OCI_MCP_NAME", "oci-mcp"),
                transport=TransportType(os.getenv("OCI_MCP_TRANSPORT", "stdio")),
                port=int(os.getenv("OCI_MCP_PORT", "8000")),
                log_level=os.getenv("OCI_MCP_LOG_LEVEL", "INFO"),
                allow_mutations=os.getenv("ALLOW_MUTATIONS", "false").lower() == "true",
            ),
            oci=OCIConfig(
                auth_method=AuthMethod(os.getenv("OCI_AUTH_METHOD", "config_file")),
                config_file=Path(os.getenv("OCI_CONFIG_FILE", "~/.oci/config")),
                profile=os.getenv("OCI_PROFILE", "DEFAULT"),
                tenancy_ocid=os.getenv("OCI_TENANCY_OCID"),
                region=os.getenv("OCI_REGION"),
                compartment_ocid=os.getenv("COMPARTMENT_OCID"),
            ),
            observability=ObservabilityConfig(
                apm=APMConfig(
                    enabled=bool(os.getenv("OCI_APM_ENDPOINT")),
                    endpoint=os.getenv("OCI_APM_ENDPOINT"),
                    private_data_key=os.getenv("OCI_APM_PRIVATE_DATA_KEY"),
                    domain_id=os.getenv("OCI_APM_DOMAIN_ID"),
                ),
                logging=LoggingConfig(
                    enabled=os.getenv("OCI_LOGGING_ENABLED", "false").lower() == "true",
                    log_id=os.getenv("OCI_LOGGING_LOG_ID"),
                    compartment_id=os.getenv("OCI_LOGGING_COMPARTMENT_ID"),
                ),
                log_analytics=LogAnalyticsConfig(
                    enabled=bool(os.getenv("OCI_LOGAN_NAMESPACE")),
                    namespace=os.getenv("OCI_LOGAN_NAMESPACE"),
                    log_group_id=os.getenv("OCI_LOGAN_LOG_GROUP_ID"),
                    source_name=os.getenv("OCI_LOGAN_SOURCE_NAME", "oci-mcp-server"),
                    entity_id=os.getenv("OCI_LOGAN_ENTITY_ID"),
                ),
            ),
        )

    def validate_required(self) -> list[str]:
        """Validate required configuration and return list of missing items."""
        missing = []

        # OCI config file must exist if using config_file auth
        is_config_auth = self.oci.auth_method == AuthMethod.CONFIG_FILE
        if is_config_auth and not self.oci.config_file.exists():
            missing.append(f"OCI config file not found: {self.oci.config_file}")

        return missing


# Global config instance (lazy-loaded)
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def reset_config() -> None:
    """Reset the global configuration (useful for testing)."""
    global _config
    _config = None
