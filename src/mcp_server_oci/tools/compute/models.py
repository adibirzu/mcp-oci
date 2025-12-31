"""
Pydantic models for OCI Compute domain tools.

All models use Pydantic v2 with ConfigDict for validation.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Import canonical ResponseFormat from core
from mcp_server_oci.core.formatters import ResponseFormat


class LifecycleState(str, Enum):
    """Instance lifecycle states."""
    MOVING = "MOVING"
    PROVISIONING = "PROVISIONING"
    RUNNING = "RUNNING"
    STARTING = "STARTING"
    STOPPED = "STOPPED"
    STOPPING = "STOPPING"
    TERMINATED = "TERMINATED"
    TERMINATING = "TERMINATING"
    CREATING_IMAGE = "CREATING_IMAGE"


# =============================================================================
# Input Models
# =============================================================================

class ListInstancesInput(BaseModel):
    """Input for listing compute instances."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID (defaults to COMPARTMENT_OCID env var)"
    )
    lifecycle_state: LifecycleState | None = Field(
        default=None,
        description="Filter by lifecycle state (RUNNING, STOPPED, etc.)"
    )
    display_name: str | None = Field(
        default=None,
        description="Filter by display name (partial match)"
    )
    limit: int = Field(
        default=20,
        description="Maximum results to return",
        ge=1,
        le=100
    )
    offset: int = Field(
        default=0,
        description="Number of results to skip",
        ge=0
    )
    include_ips: bool = Field(
        default=False,
        description="Include IP addresses (slower, requires additional API calls)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable, 'json' for machine-readable"
    )


class GetInstanceInput(BaseModel):
    """Input for getting a single instance."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    instance_id: str = Field(
        ...,
        description="Instance OCID (e.g., 'ocid1.instance.oc1...')",
        min_length=20
    )
    include_metrics: bool = Field(
        default=False,
        description="Include recent CPU/memory metrics"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )

    @field_validator('instance_id')
    @classmethod
    def validate_instance_id(cls, v: str) -> str:
        if not v.startswith('ocid1.instance.'):
            raise ValueError("Invalid instance OCID. Expected format: ocid1.instance.oc1...")
        return v


class InstanceActionInput(BaseModel):
    """Input for instance actions (start/stop/restart)."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    instance_id: str = Field(
        ...,
        description="Instance OCID to act on",
        min_length=20
    )
    force: bool = Field(
        default=False,
        description="Force the action (e.g., hard stop instead of soft)"
    )
    wait_for_state: bool = Field(
        default=False,
        description="Wait for the instance to reach target state"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )

    @field_validator('instance_id')
    @classmethod
    def validate_instance_id(cls, v: str) -> str:
        if not v.startswith('ocid1.instance.'):
            raise ValueError("Invalid instance OCID. Expected format: ocid1.instance.oc1...")
        return v


class GetInstanceMetricsInput(BaseModel):
    """Input for getting instance metrics."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    instance_id: str = Field(
        ...,
        description="Instance OCID"
    )
    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID (defaults to COMPARTMENT_OCID env var)"
    )
    metric_names: list[str] = Field(
        default=["CpuUtilization", "MemoryUtilization"],
        description="Metrics to retrieve"
    )
    hours_back: int = Field(
        default=1,
        description="Hours of historical data",
        ge=1,
        le=168  # 7 days
    )
    time_window: str = Field(
        default="1h",
        description="Time window for metrics (e.g., '1h', '24h', '7d')"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )


# =============================================================================
# Output Models
# =============================================================================

class InstanceSummary(BaseModel):
    """Summary of a compute instance."""
    id: str = Field(description="Instance OCID")
    display_name: str = Field(description="Display name")
    lifecycle_state: str = Field(description="Current state")
    shape: str = Field(description="Instance shape")
    availability_domain: str | None = Field(default=None, description="AD name")
    fault_domain: str | None = Field(default=None, description="Fault domain")
    time_created: str | None = Field(default=None, description="Creation time")
    public_ip: str | None = Field(default=None, description="Public IP if assigned")
    private_ip: str | None = Field(default=None, description="Private IP")
    compartment_id: str | None = Field(default=None, description="Compartment OCID")
    region: str | None = Field(default=None, description="Region")


class ListInstancesOutput(BaseModel):
    """Output for list instances operation."""
    total: int = Field(description="Total available (may be approximate)")
    count: int = Field(description="Results in this response")
    offset: int = Field(description="Current offset")
    instances: list[InstanceSummary] = Field(description="Instance list")
    has_more: bool = Field(description="More results available")
    next_offset: int | None = Field(default=None, description="Offset for next page")


class InstanceActionOutput(BaseModel):
    """Output for instance action operations."""
    success: bool = Field(description="Whether action was initiated")
    instance_id: str = Field(description="Instance OCID")
    action: str = Field(description="Action performed")
    previous_state: str | None = Field(default=None, description="State before action")
    target_state: str = Field(description="Expected final state")
    message: str = Field(description="Status message")


class MetricDataPoint(BaseModel):
    """Single metric data point."""
    timestamp: str = Field(description="ISO timestamp")
    value: float = Field(description="Metric value")


class InstanceMetricsOutput(BaseModel):
    """Output for instance metrics."""
    instance_id: str = Field(description="Instance OCID")
    instance_name: str | None = Field(default=None, description="Display name")
    period_start: str = Field(description="Data start time")
    period_end: str = Field(description="Data end time")
    metrics: dict[str, dict] = Field(description="Metrics by name with stats")
