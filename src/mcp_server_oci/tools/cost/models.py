"""
Pydantic models for OCI Cost domain tools.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Granularity(str, Enum):
    """Time granularity for cost queries."""
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"


class ResponseFormat(str, Enum):
    """Output format for responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class BaseCostInput(BaseModel):
    """Base model for all cost tool inputs."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable, 'json' for machine-readable"
    )


class CostSummaryInput(BaseCostInput):
    """Input for cost summary queries."""

    tenancy_ocid: str = Field(
        ...,
        description="OCI Tenancy OCID (e.g., 'ocid1.tenancy.oc1..aaaaaa')",
        min_length=20
    )
    time_start: str = Field(
        ...,
        description="Start date in ISO format (e.g., '2024-01-01T00:00:00Z')"
    )
    time_end: str = Field(
        ...,
        description="End date in ISO format (e.g., '2024-01-31T23:59:59Z')"
    )
    granularity: Granularity = Field(
        default=Granularity.DAILY,
        description="Time granularity: DAILY or MONTHLY"
    )

    @field_validator('tenancy_ocid')
    @classmethod
    def validate_tenancy_ocid(cls, v: str) -> str:
        if not v.startswith('ocid1.tenancy.'):
            raise ValueError("Invalid tenancy OCID format. Expected 'ocid1.tenancy.oc1...'")
        return v

    @field_validator('time_start', 'time_end')
    @classmethod
    def validate_datetime(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid datetime format: {v}. Use ISO format (e.g., '2024-01-01T00:00:00Z').")
        return v


class CostByCompartmentInput(BaseCostInput):
    """Input for compartment cost breakdown."""

    tenancy_ocid: str = Field(
        ...,
        description="OCI Tenancy OCID",
        min_length=20
    )
    time_start: str = Field(
        ...,
        description="Start date in ISO format"
    )
    time_end: str = Field(
        ...,
        description="End date in ISO format"
    )
    scope_compartment_id: str | None = Field(
        default=None,
        description="Limit to specific compartment OCID"
    )
    include_children: bool = Field(
        default=False,
        description="Include child compartment costs"
    )
    compartment_depth: int = Field(
        default=0,
        description="Compartment hierarchy depth (0=root, 1=first level, etc.)",
        ge=0,
        le=5
    )
    granularity: Granularity = Field(
        default=Granularity.DAILY,
        description="Time granularity"
    )
    top_n: int = Field(
        default=10,
        description="Number of top compartments to return",
        ge=1,
        le=50
    )


class CostByServiceInput(BaseCostInput):
    """Input for service cost drilldown."""

    tenancy_ocid: str = Field(
        ...,
        description="OCI Tenancy OCID",
        min_length=20
    )
    time_start: str = Field(
        ...,
        description="Start date in ISO format"
    )
    time_end: str = Field(
        ...,
        description="End date in ISO format"
    )
    top_n: int = Field(
        default=10,
        description="Number of top services to return",
        ge=1,
        le=50
    )
    scope_compartment_id: str | None = Field(
        default=None,
        description="Limit to specific compartment"
    )
    include_children: bool = Field(
        default=False,
        description="Include child compartment costs"
    )


class MonthlyTrendInput(BaseCostInput):
    """Input for monthly cost trend analysis."""

    tenancy_ocid: str = Field(
        ...,
        description="OCI Tenancy OCID",
        min_length=20
    )
    months_back: int = Field(
        default=6,
        description="Number of months to analyze",
        ge=1,
        le=24
    )
    include_forecast: bool = Field(
        default=True,
        description="Include cost forecast for next month"
    )
    budget_ocid: str | None = Field(
        default=None,
        description="Budget OCID for variance analysis"
    )


class CostAnomalyInput(BaseCostInput):
    """Input for cost anomaly detection."""

    tenancy_ocid: str = Field(
        ...,
        description="OCI Tenancy OCID",
        min_length=20
    )
    time_start: str = Field(
        ...,
        description="Start date in ISO format"
    )
    time_end: str = Field(
        ...,
        description="End date in ISO format"
    )
    threshold: float = Field(
        default=2.0,
        description="Standard deviations for anomaly detection",
        ge=1.0,
        le=5.0
    )
    top_n: int = Field(
        default=10,
        description="Maximum number of anomalies to return",
        ge=1,
        le=50
    )
    scope_compartment_id: str | None = Field(
        default=None,
        description="Limit to specific compartment"
    )
    include_children: bool = Field(
        default=False,
        description="Include child compartments"
    )


# Output models for structured responses

class CostItem(BaseModel):
    """Single cost item in responses."""
    date: str
    amount: float
    currency: str = "USD"
    service: str | None = None
    compartment: str | None = None


class ServiceCost(BaseModel):
    """Service cost breakdown."""
    service: str
    cost: float
    percentage: float
    currency: str = "USD"


class CompartmentCost(BaseModel):
    """Compartment cost breakdown."""
    compartment_id: str
    compartment_name: str
    cost: float
    percentage: float
    currency: str = "USD"
    services: list[ServiceCost] = []


class CostSummaryOutput(BaseModel):
    """Structured cost summary output."""
    total_cost: float
    currency: str = "USD"
    period_start: str
    period_end: str
    daily_average: float
    by_service: list[ServiceCost] = []
    by_compartment: list[CompartmentCost] = []
    forecast: dict | None = None


class CostAnomaly(BaseModel):
    """Cost anomaly detection result."""
    date: str
    cost: float
    expected_cost: float
    deviation_percent: float
    severity: str  # low, medium, high, critical
    root_cause: dict | None = None


class AnomalyDetectionOutput(BaseModel):
    """Output for cost anomaly detection."""
    anomalies: list[CostAnomaly]
    detection_params: dict
    summary: dict
