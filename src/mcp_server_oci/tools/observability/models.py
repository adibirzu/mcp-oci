"""Pydantic models for OCI Observability domain tools.

Provides models for metrics, logs, and monitoring operations.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResponseFormat(str, Enum):
    """Output format for responses."""

    MARKDOWN = "markdown"
    JSON = "json"


class TimeWindow(str, Enum):
    """Time windows for queries."""

    MINUTES_15 = "15m"
    MINUTES_30 = "30m"
    HOUR_1 = "1h"
    HOURS_3 = "3h"
    HOURS_6 = "6h"
    HOURS_12 = "12h"
    HOURS_24 = "24h"
    DAYS_7 = "7d"


class MetricNamespace(str, Enum):
    """OCI metric namespaces."""

    COMPUTE = "oci_computeagent"
    BLOCK_STORAGE = "oci_blockstore"
    DATABASE = "oci_database"
    LOAD_BALANCER = "oci_lbaas"
    VCN = "oci_vcn"
    OBJECT_STORAGE = "oci_objectstorage"


class GetInstanceMetricsInput(BaseModel):
    """Input for getting compute instance metrics."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    instance_id: str = Field(
        ...,
        description="Compute instance OCID (e.g., 'ocid1.instance.oc1.xxx')",
        min_length=20,
    )
    compartment_id: Optional[str] = Field(
        default=None,
        description="Compartment OCID (defaults to instance compartment)",
    )
    window: TimeWindow = Field(
        default=TimeWindow.HOUR_1,
        description="Time window for metrics (e.g., '1h', '24h', '7d')",
    )
    include_memory: bool = Field(
        default=True,
        description="Include memory utilization metrics",
    )
    include_disk: bool = Field(
        default=False,
        description="Include disk I/O metrics",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'",
    )

    @field_validator("instance_id")
    @classmethod
    def validate_instance_id(cls, v: str) -> str:
        if not v.startswith("ocid1.instance."):
            raise ValueError("Invalid instance OCID format. Expected 'ocid1.instance.oc1...'")
        return v


class GetMetricsInput(BaseModel):
    """Input for getting generic metrics."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    resource_id: str = Field(
        ...,
        description="Resource OCID to get metrics for",
        min_length=20,
    )
    compartment_id: Optional[str] = Field(
        default=None,
        description="Compartment OCID (defaults to resource compartment)",
    )
    namespace: MetricNamespace = Field(
        ...,
        description="OCI metric namespace (e.g., 'oci_computeagent')",
    )
    metric_name: str = Field(
        ...,
        description="Metric name (e.g., 'CpuUtilization', 'MemoryUtilization')",
    )
    window: TimeWindow = Field(
        default=TimeWindow.HOUR_1,
        description="Time window for metrics",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'",
    )


class ExecuteLogQueryInput(BaseModel):
    """Input for executing Log Analytics queries."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    query: str = Field(
        ...,
        description="Log Analytics query string (e.g., \"* | stats count by 'Log Source'\")",
        min_length=1,
    )
    compartment_id: Optional[str] = Field(
        default=None,
        description="Compartment OCID to scope the query (defaults to env var)",
    )
    time_range: str = Field(
        default="60m",
        description="Time range (e.g., '60m', '24h', '7d')",
    )
    limit: int = Field(
        default=100,
        description="Maximum results to return",
        ge=1,
        le=1000,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'",
    )


class ListAlarmsInput(BaseModel):
    """Input for listing monitoring alarms."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    compartment_id: Optional[str] = Field(
        default=None,
        description="Compartment OCID (defaults to tenancy root)",
    )
    lifecycle_state: Optional[str] = Field(
        default=None,
        description="Filter by lifecycle state (e.g., 'ACTIVE', 'INACTIVE')",
    )
    severity: Optional[str] = Field(
        default=None,
        description="Filter by severity (e.g., 'CRITICAL', 'WARNING', 'INFO')",
    )
    limit: int = Field(
        default=50,
        description="Maximum alarms to return",
        ge=1,
        le=200,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'",
    )


class GetAlarmHistoryInput(BaseModel):
    """Input for getting alarm history."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    alarm_id: str = Field(
        ...,
        description="Alarm OCID",
        min_length=20,
    )
    window: TimeWindow = Field(
        default=TimeWindow.HOURS_24,
        description="Time window for history",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'",
    )

    @field_validator("alarm_id")
    @classmethod
    def validate_alarm_id(cls, v: str) -> str:
        if not v.startswith("ocid1.alarm."):
            raise ValueError("Invalid alarm OCID format. Expected 'ocid1.alarm.oc1...'")
        return v


class ListLogSourcesInput(BaseModel):
    """Input for listing Log Analytics sources."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    compartment_id: Optional[str] = Field(
        default=None,
        description="Compartment OCID (defaults to tenancy)",
    )
    source_type: Optional[str] = Field(
        default=None,
        description="Filter by source type (e.g., 'LOG', 'FILE')",
    )
    name_contains: Optional[str] = Field(
        default=None,
        description="Filter by name containing string",
    )
    limit: int = Field(
        default=50,
        description="Maximum sources to return",
        ge=1,
        le=200,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'",
    )


class ObservabilityOverviewInput(BaseModel):
    """Input for observability overview skill."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    compartment_id: Optional[str] = Field(
        default=None,
        description="Compartment OCID (defaults to tenancy)",
    )
    include_alarms: bool = Field(
        default=True,
        description="Include active alarms in overview",
    )
    include_log_sources: bool = Field(
        default=True,
        description="Include Log Analytics sources summary",
    )
    window: TimeWindow = Field(
        default=TimeWindow.HOURS_24,
        description="Time window for recent activity",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'",
    )
