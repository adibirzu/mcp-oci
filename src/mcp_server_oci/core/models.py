"""
Base Pydantic models for OCI MCP Server tools.

Provides standardized input/output models with validation and documentation.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .formatters import ResponseFormat


class Granularity(str, Enum):
    """Time granularity for queries."""
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    HOURLY = "HOURLY"


class SortOrder(str, Enum):
    """Sort order for list operations."""
    ASC = "ASC"
    DESC = "DESC"


class BaseToolInput(BaseModel):
    """Base model for all tool inputs."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid',
        use_enum_values=True
    )
    
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable, 'json' for machine-readable"
    )


class OCIContextInput(BaseToolInput):
    """Base model for OCI tools with context injection support.
    
    These fields can be injected by the ToolCatalog.setContext() on the client side.
    """
    
    profile: Optional[str] = Field(
        default=None,
        description="OCI CLI profile name (default: from OCI_PROFILE env var)"
    )
    region: Optional[str] = Field(
        default=None,
        description="OCI region override (e.g., 'us-ashburn-1')"
    )
    compartment_id: Optional[str] = Field(
        default=None,
        description="Compartment OCID for scoping operations"
    )
    
    @field_validator('compartment_id')
    @classmethod
    def validate_compartment_ocid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith('ocid1.compartment.') and not v.startswith('ocid1.tenancy.'):
            raise ValueError(
                "Invalid compartment OCID format. Expected 'ocid1.compartment.oc1...' or 'ocid1.tenancy.oc1...'"
            )
        return v


class TenancyInput(OCIContextInput):
    """Base model for tools that require tenancy context."""
    
    tenancy_ocid: str = Field(
        ...,
        description="OCI Tenancy OCID (e.g., 'ocid1.tenancy.oc1..aaaaaa')",
        min_length=20
    )
    
    @field_validator('tenancy_ocid')
    @classmethod
    def validate_tenancy_ocid(cls, v: str) -> str:
        if not v.startswith('ocid1.tenancy.'):
            raise ValueError("Invalid tenancy OCID format. Expected 'ocid1.tenancy.oc1...'")
        return v


class TimeRangeInput(OCIContextInput):
    """Base model for tools that query a time range."""
    
    time_start: str = Field(
        ...,
        description="Start time in ISO format (e.g., '2024-01-01T00:00:00Z')"
    )
    time_end: str = Field(
        ...,
        description="End time in ISO format (e.g., '2024-01-31T23:59:59Z')"
    )
    
    @field_validator('time_start', 'time_end')
    @classmethod
    def validate_datetime(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid datetime format: {v}. Use ISO format: YYYY-MM-DDTHH:MM:SSZ")
        return v


class PaginatedInput(BaseToolInput):
    """Base model for paginated list operations."""
    
    limit: int = Field(
        default=20,
        description="Maximum results to return (1-100)",
        ge=1,
        le=100
    )
    offset: int = Field(
        default=0,
        description="Number of results to skip for pagination",
        ge=0
    )
    sort_by: Optional[str] = Field(
        default=None,
        description="Field to sort results by"
    )
    sort_order: SortOrder = Field(
        default=SortOrder.ASC,
        description="Sort order: ASC or DESC"
    )


class OCIPaginatedInput(OCIContextInput, PaginatedInput):
    """Combined OCI context with pagination support."""
    pass


T = TypeVar('T')


class PaginatedOutput(BaseModel, Generic[T]):
    """Standard pagination response wrapper."""
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    
    total: int = Field(description="Total available results")
    count: int = Field(description="Number of results in this response")
    offset: int = Field(description="Current offset")
    items: list[T] = Field(description="Result items")
    has_more: bool = Field(description="Whether more results are available")
    next_offset: Optional[int] = Field(
        default=None,
        description="Offset for next page (None if no more pages)"
    )
    
    @classmethod
    def from_items(
        cls,
        items: list[T],
        total: int,
        offset: int = 0,
        limit: int = 20
    ) -> "PaginatedOutput[T]":
        """Create paginated output from items list."""
        count = len(items)
        has_more = offset + count < total
        next_offset = offset + count if has_more else None
        
        return cls(
            total=total,
            count=count,
            offset=offset,
            items=items,
            has_more=has_more,
            next_offset=next_offset
        )


class ToolMetadata(BaseModel):
    """Metadata about a tool for discovery."""
    
    name: str = Field(description="Tool name")
    domain: str = Field(description="Domain the tool belongs to")
    summary: str = Field(description="One-line description")
    tier: int = Field(
        default=2,
        description="Performance tier (1=instant, 2=API, 3=heavy, 4=admin)",
        ge=1,
        le=4
    )
    read_only: bool = Field(default=True, description="Whether tool is read-only")
    
    model_config = ConfigDict(
        frozen=True  # Immutable
    )


class HealthStatus(BaseModel):
    """Health check response."""
    
    status: str = Field(description="Overall status: healthy, degraded, unhealthy")
    version: str = Field(description="Server version")
    uptime_seconds: float = Field(description="Server uptime in seconds")
    checks: dict[str, Any] = Field(
        default_factory=dict,
        description="Individual health check results"
    )
    timestamp: str = Field(description="ISO timestamp of check")


class ServerManifest(BaseModel):
    """Server manifest for client optimization."""
    
    name: str = Field(description="Server identifier")
    version: str = Field(description="Semantic version")
    description: str = Field(description="Brief description")
    domains: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Available domains with tool counts"
    )
    capabilities: dict[str, Any] = Field(
        default_factory=dict,
        description="Server capabilities grouped by tier"
    )
    environment_variables: list[str] = Field(
        default_factory=list,
        description="Required environment variable names"
    )
    usage_guide: str = Field(
        default="",
        description="Quick start instructions"
    )
