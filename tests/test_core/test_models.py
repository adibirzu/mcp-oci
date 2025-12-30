"""
Tests for core models module.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_server_oci.core.models import (
    ResponseFormat,
    Granularity,
    BaseToolInput,
    OCIContextInput,
    PaginatedInput,
    PaginatedOutput,
)


class TestResponseFormat:
    """Tests for ResponseFormat enum."""
    
    def test_values(self):
        """Test enum values."""
        assert ResponseFormat.MARKDOWN.value == "markdown"
        assert ResponseFormat.JSON.value == "json"
    
    def test_from_string(self):
        """Test creating from string."""
        assert ResponseFormat("markdown") == ResponseFormat.MARKDOWN
        assert ResponseFormat("json") == ResponseFormat.JSON


class TestGranularity:
    """Tests for Granularity enum."""
    
    def test_values(self):
        """Test enum values."""
        assert Granularity.DAILY.value == "DAILY"
        assert Granularity.MONTHLY.value == "MONTHLY"
        assert Granularity.HOURLY.value == "HOURLY"


class TestBaseToolInput:
    """Tests for BaseToolInput model."""
    
    def test_default_response_format(self):
        """Test default response format is markdown."""
        input_model = BaseToolInput()
        assert input_model.response_format == ResponseFormat.MARKDOWN
    
    def test_json_response_format(self):
        """Test setting JSON response format."""
        input_model = BaseToolInput(response_format=ResponseFormat.JSON)
        assert input_model.response_format == ResponseFormat.JSON
    
    def test_from_string_format(self):
        """Test creating with string format."""
        input_model = BaseToolInput(response_format="json")
        assert input_model.response_format == ResponseFormat.JSON
    
    def test_invalid_format_rejected(self):
        """Test that invalid format raises error."""
        with pytest.raises(ValidationError):
            BaseToolInput(response_format="invalid")
    
    def test_extra_fields_forbidden(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            BaseToolInput(unknown_field="value")


class TestOCIContextInput:
    """Tests for OCIContextInput model."""
    
    def test_defaults(self):
        """Test default values."""
        input_model = OCIContextInput()
        assert input_model.profile is None
        assert input_model.region is None
        assert input_model.compartment_id is None
        assert input_model.response_format == ResponseFormat.MARKDOWN
    
    def test_with_context(self):
        """Test with OCI context values."""
        input_model = OCIContextInput(
            profile="PRODUCTION",
            region="us-ashburn-1",
            compartment_id="ocid1.compartment.oc1..aaaaaa"
        )
        assert input_model.profile == "PRODUCTION"
        assert input_model.region == "us-ashburn-1"
        assert input_model.compartment_id == "ocid1.compartment.oc1..aaaaaa"
    
    def test_whitespace_stripped(self):
        """Test that whitespace is stripped from strings."""
        input_model = OCIContextInput(
            profile="  PRODUCTION  ",
            region="  us-ashburn-1  "
        )
        assert input_model.profile == "PRODUCTION"
        assert input_model.region == "us-ashburn-1"


class TestPaginatedInput:
    """Tests for PaginatedInput model."""
    
    def test_defaults(self):
        """Test default values."""
        input_model = PaginatedInput()
        assert input_model.limit == 20
        assert input_model.offset == 0
    
    def test_custom_values(self):
        """Test custom pagination values."""
        input_model = PaginatedInput(limit=50, offset=100)
        assert input_model.limit == 50
        assert input_model.offset == 100
    
    def test_limit_minimum(self):
        """Test limit minimum constraint."""
        with pytest.raises(ValidationError):
            PaginatedInput(limit=0)
    
    def test_limit_maximum(self):
        """Test limit maximum constraint."""
        with pytest.raises(ValidationError):
            PaginatedInput(limit=101)
    
    def test_offset_minimum(self):
        """Test offset minimum constraint."""
        with pytest.raises(ValidationError):
            PaginatedInput(offset=-1)
    
    def test_valid_boundary_values(self):
        """Test valid boundary values."""
        # Minimum valid limit
        input_min = PaginatedInput(limit=1, offset=0)
        assert input_min.limit == 1
        
        # Maximum valid limit
        input_max = PaginatedInput(limit=100, offset=0)
        assert input_max.limit == 100


class TestPaginatedOutput:
    """Tests for PaginatedOutput model."""
    
    def test_creation(self):
        """Test creating paginated output."""
        output = PaginatedOutput(
            total=100,
            count=20,
            offset=0,
            items=[{"id": 1}, {"id": 2}],
            has_more=True,
            next_offset=20
        )
        
        assert output.total == 100
        assert output.count == 20
        assert output.offset == 0
        assert len(output.items) == 2
        assert output.has_more is True
        assert output.next_offset == 20
    
    def test_last_page(self):
        """Test last page with no more results."""
        output = PaginatedOutput(
            total=50,
            count=10,
            offset=40,
            items=[{"id": 41}],
            has_more=False,
            next_offset=None
        )
        
        assert output.has_more is False
        assert output.next_offset is None
    
    def test_model_dump(self):
        """Test serialization."""
        output = PaginatedOutput(
            total=100,
            count=20,
            offset=0,
            items=["item1", "item2"],
            has_more=True,
            next_offset=20
        )
        
        data = output.model_dump()
        
        assert data["total"] == 100
        assert data["count"] == 20
        assert data["has_more"] is True
        assert "items" in data
