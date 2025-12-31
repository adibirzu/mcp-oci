"""
Comprehensive error handling for OCI MCP operations.

Provides structured errors with actionable suggestions for users.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

try:
    import oci.exceptions
    HAS_OCI = True
except ImportError:
    HAS_OCI = False


class ErrorCategory(str, Enum):
    """Error categories for user-friendly messaging."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    SERVICE = "service"
    NETWORK = "network"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class OCIError:
    """Structured OCI error with actionable suggestions."""

    category: ErrorCategory
    message: str
    suggestion: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_string(self) -> str:
        """Format error as user-friendly string."""
        return f"Error ({self.category.value}): {self.message}\n\nSuggestion: {self.suggestion}"

    def to_dict(self) -> dict[str, Any]:
        """Format error as structured dictionary."""
        return {
            "success": False,
            "error": self.message,
            "category": self.category.value,
            "suggestion": self.suggestion,
            "details": self.details
        }

    def to_json(self) -> str:
        """Format error as JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        """Format error as markdown."""
        md = "## ❌ Error\n\n"
        md += f"**Category:** {self.category.value}\n"
        md += f"**Message:** {self.message}\n\n"
        md += f"**Suggestion:** {self.suggestion}\n"

        if self.details:
            md += "\n### Details\n"
            for key, value in self.details.items():
                md += f"- **{key}:** {value}\n"

        return md


# Error mapping table: status_code -> (category, base_message, suggestion)
ERROR_MAP: dict[int, tuple[ErrorCategory, str, str]] = {
    400: (
        ErrorCategory.VALIDATION,
        "Invalid request parameters",
        "Check the input parameters match the expected format and constraints."
    ),
    401: (
        ErrorCategory.AUTHENTICATION,
        "Authentication failed",
        "Verify your OCI credentials are valid and the API key is not expired."
    ),
    403: (
        ErrorCategory.AUTHORIZATION,
        "Permission denied",
        "Ensure your user/group has the required IAM policies for this operation."
    ),
    404: (
        ErrorCategory.NOT_FOUND,
        "Resource not found",
        "Verify the OCID is correct and the resource exists in the specified region."
    ),
    409: (
        ErrorCategory.SERVICE,
        "Resource conflict",
        "The resource may be in a transitional state. Wait and retry."
    ),
    429: (
        ErrorCategory.RATE_LIMIT,
        "Rate limit exceeded",
        "Wait 60 seconds before retrying. Consider reducing request frequency."
    ),
    500: (
        ErrorCategory.SERVICE,
        "OCI service error",
        "This is an OCI-side issue. Check OCI status page and retry later."
    ),
    503: (
        ErrorCategory.SERVICE,
        "Service temporarily unavailable",
        "OCI service is experiencing issues. Check status.oracle.com and retry later."
    ),
}


def handle_oci_error(e: Exception, context: str | None = None) -> OCIError:
    """
    Convert OCI exceptions to structured errors with actionable suggestions.
    
    Args:
        e: The exception to handle
        context: Optional context about the operation being performed
        
    Returns:
        OCIError with category, message, and suggestion
    """
    if HAS_OCI and isinstance(e, oci.exceptions.ServiceError):
        status = e.status
        category, base_message, suggestion = ERROR_MAP.get(
            status,
            (ErrorCategory.UNKNOWN, f"Unexpected error (status {status})", "Check the error details and retry.")
        )

        message = base_message
        if context:
            message = f"{base_message} while {context}"
        if hasattr(e, 'message') and e.message:
            message = f"{message}: {e.message}"

        return OCIError(
            category=category,
            message=message,
            suggestion=suggestion,
            details={
                "status": status,
                "code": getattr(e, 'code', None),
                "opc_request_id": getattr(e, 'request_id', None),
            }
        )

    if HAS_OCI and isinstance(e, oci.exceptions.ClientError):
        return OCIError(
            category=ErrorCategory.NETWORK,
            message=f"Network error{f' while {context}' if context else ''}: {str(e)}",
            suggestion="Check your network connection and OCI endpoint accessibility."
        )

    if HAS_OCI and isinstance(e, oci.exceptions.ConfigFileNotFound):
        return OCIError(
            category=ErrorCategory.AUTHENTICATION,
            message="OCI config file not found",
            suggestion="Ensure ~/.oci/config exists or set OCI_CONFIG_FILE environment variable."
        )

    # Handle timeout errors
    if "timeout" in str(e).lower():
        return OCIError(
            category=ErrorCategory.TIMEOUT,
            message=f"Request timeout{f' while {context}' if context else ''}",
            suggestion="The operation took too long. Try with a smaller scope or retry later."
        )

    # Generic fallback
    return OCIError(
        category=ErrorCategory.UNKNOWN,
        message=f"Unexpected error{f' while {context}' if context else ''}: {str(e)}",
        suggestion="Check the error details. If the issue persists, report it."
    )


def format_error_response(error: OCIError, response_format: str = "markdown") -> str:
    """
    Format error for tool response based on requested format.
    
    Args:
        error: The OCIError to format
        response_format: Output format - "markdown" or "json"
        
    Returns:
        Formatted error string
    """
    if response_format.lower() == "json":
        return error.to_json()
    return error.to_markdown()


def create_validation_error(
    field: str,
    value: Any,
    expected: str,
    context: str | None = None
) -> OCIError:
    """
    Create a validation error for invalid input.
    
    Args:
        field: The field name that failed validation
        value: The invalid value
        expected: Description of expected format
        context: Optional context about the operation
        
    Returns:
        OCIError for the validation failure
    """
    return OCIError(
        category=ErrorCategory.VALIDATION,
        message=f"Invalid value for '{field}'{f' while {context}' if context else ''}: got '{value}'",
        suggestion=f"Expected: {expected}",
        details={
            "field": field,
            "value": str(value),
            "expected": expected
        }
    )


def create_not_found_error(
    resource_type: str,
    identifier: str,
    context: str | None = None
) -> OCIError:
    """
    Create a not found error for missing resources.
    
    Args:
        resource_type: Type of resource (e.g., "instance", "compartment")
        identifier: The OCID or name that was not found
        context: Optional context about the operation
        
    Returns:
        OCIError for the not found condition
    """
    # Mask OCID for safety
    if identifier.startswith("ocid1.") and len(identifier) > 30:
        masked = f"{identifier[:25]}...{identifier[-5:]}"
    else:
        masked = identifier

    return OCIError(
        category=ErrorCategory.NOT_FOUND,
        message=f"{resource_type} not found: {masked}",
        suggestion=f"Verify the {resource_type} OCID is correct and exists in the specified region.",
        details={
            "resource_type": resource_type,
            "identifier": masked
        }
    )
