"""Pydantic models for OCI Security domain tools.

Follows OCI MCP Server Standard v2.1 with Pydantic v2 patterns.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ResponseFormat(str, Enum):
    """Output format for responses."""

    MARKDOWN = "markdown"
    JSON = "json"


class UserLifecycleState(str, Enum):
    """IAM user lifecycle states."""

    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DELETING = "DELETING"
    DELETED = "DELETED"


class ProblemLifecycleState(str, Enum):
    """Cloud Guard problem lifecycle states."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RiskLevel(str, Enum):
    """Cloud Guard risk levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    MINOR = "MINOR"


class ListUsersInput(BaseModel):
    """Input for listing IAM users."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID (defaults to tenancy root)",
    )
    lifecycle_state: UserLifecycleState | None = Field(
        default=None,
        description="Filter by lifecycle state",
    )
    name_contains: str | None = Field(
        default=None,
        description="Filter users whose name contains this string",
    )
    limit: int = Field(
        default=20,
        description="Maximum results to return",
        ge=1,
        le=100,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable, 'json' for machine-readable",
    )


class GetUserInput(BaseModel):
    """Input for getting user details."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    user_id: str = Field(
        ...,
        description="User OCID to retrieve",
        min_length=20,
    )
    include_groups: bool = Field(
        default=True,
        description="Include group memberships",
    )
    include_api_keys: bool = Field(
        default=False,
        description="Include API key information",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


class ListGroupsInput(BaseModel):
    """Input for listing IAM groups."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID (defaults to tenancy root)",
    )
    name_contains: str | None = Field(
        default=None,
        description="Filter groups whose name contains this string",
    )
    limit: int = Field(
        default=20,
        description="Maximum results to return",
        ge=1,
        le=100,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


class ListPoliciesInput(BaseModel):
    """Input for listing IAM policies."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID to list policies from",
    )
    name_contains: str | None = Field(
        default=None,
        description="Filter policies whose name contains this string",
    )
    limit: int = Field(
        default=20,
        description="Maximum results to return",
        ge=1,
        le=100,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


class ListCloudGuardProblemsInput(BaseModel):
    """Input for listing Cloud Guard problems."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID to search for problems",
    )
    risk_level: RiskLevel | None = Field(
        default=None,
        description="Filter by risk level (CRITICAL, HIGH, MEDIUM, LOW, MINOR)",
    )
    lifecycle_state: ProblemLifecycleState | None = Field(
        default=ProblemLifecycleState.ACTIVE,
        description="Filter by lifecycle state (ACTIVE, INACTIVE)",
    )
    limit: int = Field(
        default=20,
        description="Maximum results to return",
        ge=1,
        le=100,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


class SecurityAuditInput(BaseModel):
    """Input for security audit analysis."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID to audit (defaults to tenancy root)",
    )
    include_iam: bool = Field(
        default=True,
        description="Include IAM analysis (users, groups, policies)",
    )
    include_cloud_guard: bool = Field(
        default=True,
        description="Include Cloud Guard problems",
    )
    include_network_security: bool = Field(
        default=True,
        description="Include network security analysis",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )
