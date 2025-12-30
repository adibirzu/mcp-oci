"""
Core infrastructure modules for OCI MCP Server.

This package contains:
- client: OCI SDK wrapper with async support
- errors: Structured error handling
- formatters: Response formatting utilities
- models: Base Pydantic models
- observability: OCI APM and Logging integration
- pagination: Pagination utilities
"""

from .errors import ErrorCategory, OCIError, handle_oci_error, format_error_response
from .formatters import ResponseFormat, Formatter, MarkdownFormatter, JSONFormatter, format_response
from .models import (
    Granularity,
    SortOrder,
    BaseToolInput,
    OCIContextInput,
    TenancyInput,
    TimeRangeInput,
    PaginatedInput,
    OCIPaginatedInput,
    PaginatedOutput,
    ToolMetadata,
    HealthStatus,
    ServerManifest,
)
from .errors import create_validation_error, create_not_found_error
from .formatters import format_success_response
from .client import OCIClientManager, get_client_manager, get_oci_client, get_oci_config
from .observability import (
    get_logger,
    init_observability,
    check_observability_health,
)

__all__ = [
    # Errors
    "ErrorCategory",
    "OCIError",
    "handle_oci_error",
    "format_error_response",
    # Formatters
    "ResponseFormat",
    "Formatter",
    "MarkdownFormatter",
    "JSONFormatter",
    "format_response",
    "format_success_response",
    "create_validation_error",
    "create_not_found_error",
    # Models
    "Granularity",
    "SortOrder",
    "BaseToolInput",
    "OCIContextInput",
    "TenancyInput",
    "TimeRangeInput",
    "PaginatedInput",
    "OCIPaginatedInput",
    "PaginatedOutput",
    "ToolMetadata",
    "HealthStatus",
    "ServerManifest",
    # Client
    "OCIClientManager",
    "get_client_manager",
    "get_oci_client",
    "get_oci_config",
    # Observability
    "get_logger",
    "init_observability",
    "check_observability_health",
]
