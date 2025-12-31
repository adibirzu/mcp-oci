"""
Base Pydantic models for OCI MCP Server tools.

Provides standardized input/output models with validation and documentation.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .formatters import ResponseFormat

__all__ = [
    # Enums
    "Granularity",
    "SortOrder",
    "ResponseFormat",
    # Base Input Models
    "BaseToolInput",
    "OCIContextInput",
    "TenancyInput",
    "TimeRangeInput",
    "PaginatedInput",
    "OCIPaginatedInput",
    # Output Models
    "PaginatedOutput",
    "ToolMetadata",
    "HealthStatus",
    "ServerManifest",
    # Skill Framework
    "SkillStep",
    "SkillProgress",
    "BaseSkillInput",
    "SkillMetadata",
    "SkillResult",
]


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

    profile: str | None = Field(
        default=None,
        description="OCI CLI profile name (default: from OCI_PROFILE env var)"
    )
    region: str | None = Field(
        default=None,
        description="OCI region override (e.g., 'us-ashburn-1')"
    )
    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID for scoping operations"
    )

    @field_validator('compartment_id')
    @classmethod
    def validate_compartment_ocid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        is_compartment = v.startswith('ocid1.compartment.')
        is_tenancy = v.startswith('ocid1.tenancy.')
        if not is_compartment and not is_tenancy:
            raise ValueError(
                "Invalid compartment OCID format. "
                "Expected 'ocid1.compartment.oc1...' or 'ocid1.tenancy.oc1...'"
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
        except ValueError as e:
            msg = f"Invalid datetime format: {v}. Use ISO format: YYYY-MM-DDTHH:MM:SSZ"
            raise ValueError(msg) from e
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
    sort_by: str | None = Field(
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
    next_offset: int | None = Field(
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
    ) -> PaginatedOutput[T]:
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

    healthy: bool = Field(description="Whether the server is healthy")
    server_name: str = Field(description="Server name")
    version: str = Field(description="Server version")
    oci_connected: bool = Field(description="Whether OCI is connected")
    auth_method: str | None = Field(default=None, description="OCI authentication method")
    region: str | None = Field(default=None, description="OCI region")
    observability_enabled: bool = Field(
        default=False, description="Whether observability is enabled"
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed health check results"
    )


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


# =============================================================================
# Skill Framework Models
# =============================================================================

class SkillStep(BaseModel):
    """Represents a single step in a skill workflow."""

    name: str = Field(description="Step identifier")
    description: str = Field(description="What this step does")
    tool_name: str | None = Field(default=None, description="Tool to call (if applicable)")
    status: str = Field(default="pending", description="pending|running|completed|failed|skipped")
    result: Any | None = Field(default=None, description="Step result")
    error: str | None = Field(default=None, description="Error message if failed")
    duration_ms: float | None = Field(default=None, description="Execution time in milliseconds")


class SkillProgress(BaseModel):
    """Progress tracking for skill execution."""

    skill_name: str = Field(description="Name of the executing skill")
    total_steps: int = Field(description="Total number of steps")
    completed_steps: int = Field(default=0, description="Number of completed steps")
    current_step: str | None = Field(default=None, description="Currently executing step")
    percent_complete: float = Field(default=0.0, description="Completion percentage (0-100)")
    steps: list[SkillStep] = Field(default_factory=list, description="All steps with status")

    def advance(self, step_name: str) -> None:
        """Mark a step as running and update progress."""
        self.current_step = step_name
        for step in self.steps:
            if step.name == step_name:
                step.status = "running"
                break
        self._update_percent()

    def complete_step(self, step_name: str, result: Any = None, duration_ms: float = 0) -> None:
        """Mark a step as completed."""
        for step in self.steps:
            if step.name == step_name:
                step.status = "completed"
                step.result = result
                step.duration_ms = duration_ms
                break
        self.completed_steps += 1
        self._update_percent()

    def fail_step(self, step_name: str, error: str) -> None:
        """Mark a step as failed."""
        for step in self.steps:
            if step.name == step_name:
                step.status = "failed"
                step.error = error
                break
        self._update_percent()

    def _update_percent(self) -> None:
        """Recalculate completion percentage."""
        if self.total_steps > 0:
            self.percent_complete = (self.completed_steps / self.total_steps) * 100


class BaseSkillInput(OCIContextInput):
    """Base model for all skill inputs.

    Skills are composite operations that orchestrate multiple tools.
    They inherit OCI context for consistent authentication and scoping.
    """

    verbose: bool = Field(
        default=False,
        description="Include detailed step-by-step output"
    )
    include_raw_data: bool = Field(
        default=False,
        description="Include raw tool outputs in response"
    )


class SkillMetadata(BaseModel):
    """Metadata about a skill for discovery."""

    name: str = Field(description="Skill identifier (e.g., 'troubleshoot_instance')")
    display_name: str = Field(description="Human-readable name")
    domain: str = Field(description="Primary domain (compute, network, etc.)")
    summary: str = Field(description="One-line description")
    full_description: str = Field(default="", description="Detailed description")
    input_schema: dict[str, Any] = Field(default_factory=dict, description="JSON schema for inputs")
    tools_used: list[str] = Field(default_factory=list, description="Tools this skill calls")
    tier: int = Field(default=3, description="Performance tier (skills are usually tier 3)")
    estimated_duration: str = Field(default="1-30s", description="Expected execution time")

    model_config = ConfigDict(frozen=True)


class SkillResult(BaseModel):
    """Standard result wrapper for skill execution."""

    skill_name: str = Field(description="Name of the executed skill")
    success: bool = Field(description="Whether skill completed successfully")
    summary: str = Field(description="Brief summary of results")
    details: dict[str, Any] = Field(default_factory=dict, description="Detailed findings")
    recommendations: list[str] = Field(default_factory=list, description="Action items")
    raw_data: dict[str, Any] | None = Field(
        default=None,
        description="Raw tool outputs (if include_raw_data=True)"
    )
    progress: SkillProgress | None = Field(
        default=None,
        description="Execution progress details (if verbose=True)"
    )
    execution_time_ms: float = Field(default=0, description="Total execution time")

    def to_markdown(self) -> str:
        """Format result as markdown."""
        lines = [f"# {self.skill_name} Results\n"]

        status = "✅ Success" if self.success else "❌ Failed"
        lines.append(f"**Status:** {status}\n")
        lines.append(f"## Summary\n{self.summary}\n")

        if self.details:
            lines.append("## Details")
            for key, value in self.details.items():
                if isinstance(value, dict):
                    lines.append(f"\n### {key}")
                    for k, v in value.items():
                        lines.append(f"- **{k}:** {v}")
                else:
                    lines.append(f"- **{key}:** {value}")
            lines.append("")

        if self.recommendations:
            lines.append("## Recommendations")
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        if self.progress and self.progress.steps:
            lines.append("## Execution Steps")
            for step in self.progress.steps:
                icon = {"completed": "✅", "failed": "❌", "skipped": "⏭️"}.get(step.status, "⏳")
                duration = f" ({step.duration_ms:.0f}ms)" if step.duration_ms else ""
                lines.append(f"- {icon} {step.description}{duration}")

        lines.append(f"\n*Completed in {self.execution_time_ms:.0f}ms*")
        return "\n".join(lines)
