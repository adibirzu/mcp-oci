"""
Pydantic models for OCI Network domain tools.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ResponseFormat(str, Enum):
    """Output format for responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class VcnLifecycleState(str, Enum):
    """VCN lifecycle states."""
    PROVISIONING = "PROVISIONING"
    AVAILABLE = "AVAILABLE"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"


class SubnetLifecycleState(str, Enum):
    """Subnet lifecycle states."""
    PROVISIONING = "PROVISIONING"
    AVAILABLE = "AVAILABLE"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"


# =============================================================================
# VCN Models
# =============================================================================

class ListVcnsInput(BaseModel):
    """Input for listing VCNs."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID. Uses default if not specified."
    )
    lifecycle_state: VcnLifecycleState | None = Field(
        default=None,
        description="Filter by lifecycle state"
    )
    display_name: str | None = Field(
        default=None,
        description="Filter by display name (partial match)"
    )
    limit: int = Field(
        default=20,
        description="Maximum number of VCNs to return",
        ge=1,
        le=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'"
    )


class GetVcnInput(BaseModel):
    """Input for getting VCN details."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    vcn_id: str = Field(
        ...,
        description="VCN OCID"
    )
    include_subnets: bool = Field(
        default=True,
        description="Include subnet information"
    )
    include_security_lists: bool = Field(
        default=True,
        description="Include security list information"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'"
    )


# =============================================================================
# Subnet Models
# =============================================================================

class ListSubnetsInput(BaseModel):
    """Input for listing subnets."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID. Uses default if not specified."
    )
    vcn_id: str | None = Field(
        default=None,
        description="Filter by VCN OCID"
    )
    lifecycle_state: SubnetLifecycleState | None = Field(
        default=None,
        description="Filter by lifecycle state"
    )
    display_name: str | None = Field(
        default=None,
        description="Filter by display name (partial match)"
    )
    limit: int = Field(
        default=20,
        description="Maximum number of subnets to return",
        ge=1,
        le=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'"
    )


class GetSubnetInput(BaseModel):
    """Input for getting subnet details."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    subnet_id: str = Field(
        ...,
        description="Subnet OCID"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'"
    )


# =============================================================================
# Security List Models
# =============================================================================

class ListSecurityListsInput(BaseModel):
    """Input for listing security lists."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID. Uses default if not specified."
    )
    vcn_id: str | None = Field(
        default=None,
        description="Filter by VCN OCID"
    )
    display_name: str | None = Field(
        default=None,
        description="Filter by display name (partial match)"
    )
    limit: int = Field(
        default=20,
        description="Maximum number of security lists to return",
        ge=1,
        le=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'"
    )


class AnalyzeSecurityRulesInput(BaseModel):
    """Input for analyzing security rules."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    vcn_id: str | None = Field(
        default=None,
        description="VCN OCID to analyze. Required if security_list_id not provided."
    )
    security_list_id: str | None = Field(
        default=None,
        description="Specific security list OCID to analyze"
    )
    check_risky_rules: bool = Field(
        default=True,
        description="Check for potentially risky rules (e.g., 0.0.0.0/0)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'"
    )


# =============================================================================
# Output Models
# =============================================================================

class VcnSummary(BaseModel):
    """VCN summary in responses."""
    id: str
    display_name: str
    cidr_block: str
    lifecycle_state: str
    dns_label: str | None = None
    time_created: str
    subnet_count: int | None = None


class SubnetSummary(BaseModel):
    """Subnet summary in responses."""
    id: str
    display_name: str
    cidr_block: str
    lifecycle_state: str
    availability_domain: str | None = None
    is_public: bool
    dns_label: str | None = None
    vcn_id: str


class SecurityRuleSummary(BaseModel):
    """Security rule summary."""
    direction: str  # INGRESS or EGRESS
    protocol: str
    source_or_destination: str
    port_range: str | None = None
    is_stateless: bool = False
    description: str | None = None


class RiskyRule(BaseModel):
    """Risky rule finding."""
    security_list_id: str
    security_list_name: str
    rule: SecurityRuleSummary
    risk_level: str  # HIGH, MEDIUM, LOW
    reason: str
    recommendation: str
