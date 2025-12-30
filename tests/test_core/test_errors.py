"""
Tests for core errors module.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from mcp_server_oci.core.errors import (
    ErrorCategory,
    OCIError,
    handle_oci_error,
    format_error_response,
)

# Try to import OCI exceptions for proper mocking
try:
    import oci.exceptions
    HAS_OCI = True
except ImportError:
    HAS_OCI = False


# Create mock OCI exception classes for testing
class MockServiceError(Exception):
    """Mock OCI ServiceError for testing."""
    def __init__(self, status: int, code: str, message: str, request_id: str = "req-123"):
        self.status = status
        self.code = code
        self.message = message
        self.request_id = request_id
        super().__init__(message)


class MockClientError(Exception):
    """Mock OCI ClientError for testing."""
    pass


class MockConfigFileNotFound(Exception):
    """Mock OCI ConfigFileNotFound for testing."""
    pass


class TestErrorCategory:
    """Tests for ErrorCategory enum."""
    
    def test_all_categories_exist(self):
        """Verify all expected error categories exist."""
        expected = [
            "AUTHENTICATION",
            "AUTHORIZATION", 
            "NOT_FOUND",
            "RATE_LIMIT",
            "VALIDATION",
            "SERVICE",
            "NETWORK",
            "TIMEOUT",
            "UNKNOWN",
        ]
        for cat in expected:
            assert hasattr(ErrorCategory, cat)
    
    def test_category_values(self):
        """Test category string values."""
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.NOT_FOUND.value == "not_found"
        assert ErrorCategory.RATE_LIMIT.value == "rate_limit"


class TestOCIError:
    """Tests for OCIError dataclass."""
    
    def test_basic_creation(self):
        """Test creating an OCIError."""
        error = OCIError(
            category=ErrorCategory.AUTHENTICATION,
            message="Auth failed",
            suggestion="Check credentials"
        )
        
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.message == "Auth failed"
        assert error.suggestion == "Check credentials"
        assert error.details == {}
    
    def test_creation_with_details(self):
        """Test creating an OCIError with details."""
        error = OCIError(
            category=ErrorCategory.SERVICE,
            message="Service error",
            suggestion="Retry later",
            details={"status": 500, "request_id": "abc123"}
        )
        
        assert error.details["status"] == 500
        assert error.details["request_id"] == "abc123"
    
    def test_to_dict(self):
        """Test converting error to dictionary."""
        error = OCIError(
            category=ErrorCategory.NOT_FOUND,
            message="Resource not found",
            suggestion="Check OCID",
            details={"ocid": "ocid1.instance..."}
        )
        
        result = error.to_dict()
        
        assert result["success"] is False
        assert result["error"] == "Resource not found"
        assert result["category"] == "not_found"
        assert result["suggestion"] == "Check OCID"
        assert result["details"]["ocid"] == "ocid1.instance..."
    
    def test_to_markdown(self):
        """Test converting error to markdown."""
        error = OCIError(
            category=ErrorCategory.VALIDATION,
            message="Invalid parameter",
            suggestion="Check input format"
        )
        
        result = error.to_markdown()
        
        assert "Error" in result
        assert "validation" in result
        assert "Invalid parameter" in result
        assert "Check input format" in result


class TestHandleOCIError:
    """Tests for handle_oci_error function."""
    
    @pytest.mark.skipif(not HAS_OCI, reason="OCI SDK not installed")
    def test_service_error_401_with_oci(self):
        """Test handling 401 authentication error with real OCI SDK."""
        error = oci.exceptions.ServiceError(
            status=401,
            code="NotAuthenticated",
            headers={},
            message="Not authenticated"
        )
        
        result = handle_oci_error(error, context="fetching data")
        
        assert result.category == ErrorCategory.AUTHENTICATION
        assert "authentication" in result.message.lower() or "401" in result.message
    
    @pytest.mark.skipif(not HAS_OCI, reason="OCI SDK not installed")
    def test_service_error_403_with_oci(self):
        """Test handling 403 authorization error with real OCI SDK."""
        error = oci.exceptions.ServiceError(
            status=403,
            code="NotAuthorized",
            headers={},
            message="Not authorized"
        )
        
        result = handle_oci_error(error, context="modifying resource")
        
        assert result.category == ErrorCategory.AUTHORIZATION
    
    @pytest.mark.skipif(not HAS_OCI, reason="OCI SDK not installed")
    def test_service_error_404_with_oci(self):
        """Test handling 404 not found error with real OCI SDK."""
        error = oci.exceptions.ServiceError(
            status=404,
            code="NotFound",
            headers={},
            message="Resource not found"
        )
        
        result = handle_oci_error(error)
        
        assert result.category == ErrorCategory.NOT_FOUND
        assert "not found" in result.message.lower()
    
    @pytest.mark.skipif(not HAS_OCI, reason="OCI SDK not installed")
    def test_service_error_429_with_oci(self):
        """Test handling 429 rate limit error with real OCI SDK."""
        error = oci.exceptions.ServiceError(
            status=429,
            code="TooManyRequests",
            headers={},
            message="Rate limit exceeded"
        )
        
        result = handle_oci_error(error)
        
        assert result.category == ErrorCategory.RATE_LIMIT
        assert "retry" in result.suggestion.lower() or "wait" in result.suggestion.lower()
    
    @pytest.mark.skipif(not HAS_OCI, reason="OCI SDK not installed")
    def test_service_error_500_with_oci(self):
        """Test handling 500 server error with real OCI SDK."""
        error = oci.exceptions.ServiceError(
            status=500,
            code="InternalError",
            headers={},
            message="Internal server error"
        )
        
        result = handle_oci_error(error)
        
        assert result.category == ErrorCategory.SERVICE
    
    def test_generic_exception(self):
        """Test handling generic Python exception."""
        error = ValueError("Invalid value")
        
        result = handle_oci_error(error)
        
        assert result.category == ErrorCategory.UNKNOWN
        assert "Invalid value" in result.message
    
    def test_context_included(self):
        """Test that context is included in message."""
        error = Exception("Something failed")
        
        result = handle_oci_error(error, context="processing request")
        
        assert "processing request" in result.message
    
    def test_timeout_error(self):
        """Test handling timeout exception."""
        error = Exception("Connection timeout occurred")
        
        result = handle_oci_error(error)
        
        assert result.category == ErrorCategory.TIMEOUT
        assert "timeout" in result.message.lower()


class TestFormatErrorResponse:
    """Tests for format_error_response function."""
    
    def test_format_markdown(self):
        """Test formatting error as markdown."""
        error = OCIError(
            category=ErrorCategory.AUTHENTICATION,
            message="Authentication failed",
            suggestion="Check your API key"
        )
        
        result = format_error_response(error, "markdown")
        
        assert "Error" in result
        assert "Authentication failed" in result
        assert "Check your API key" in result
    
    def test_format_json(self):
        """Test formatting error as JSON."""
        import json
        
        error = OCIError(
            category=ErrorCategory.NOT_FOUND,
            message="Instance not found",
            suggestion="Verify the OCID",
            details={"status": 404}
        )
        
        result = format_error_response(error, "json")
        parsed = json.loads(result)
        
        assert parsed["success"] is False
        assert parsed["error"] == "Instance not found"
        assert parsed["category"] == "not_found"
        assert parsed["details"]["status"] == 404
    
    def test_format_default(self):
        """Test default format (markdown)."""
        error = OCIError(
            category=ErrorCategory.SERVICE,
            message="Service unavailable",
            suggestion="Try again later"
        )
        
        result = format_error_response(error)
        
        # Default should be markdown
        assert "Error" in result or "Service unavailable" in result
