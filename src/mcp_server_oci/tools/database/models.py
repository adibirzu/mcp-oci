"""
Pydantic models for OCI Database domain tools.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ...core.models import ResponseFormat


class DatabaseType(str, Enum):
    """Database service types."""
    AUTONOMOUS = "autonomous"
    DB_SYSTEM = "db_system"
    MYSQL = "mysql"
    ALL = "all"


class ADBWorkloadType(str, Enum):
    """Autonomous Database workload types."""
    OLTP = "OLTP"
    DW = "DW"
    AJD = "AJD"
    APEX = "APEX"


class LifecycleState(str, Enum):
    """Database lifecycle states."""
    PROVISIONING = "PROVISIONING"
    AVAILABLE = "AVAILABLE"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"
    UNAVAILABLE = "UNAVAILABLE"
    RESTORE_IN_PROGRESS = "RESTORE_IN_PROGRESS"
    BACKUP_IN_PROGRESS = "BACKUP_IN_PROGRESS"
    SCALE_IN_PROGRESS = "SCALE_IN_PROGRESS"
    UPDATING = "UPDATING"
    MAINTENANCE_IN_PROGRESS = "MAINTENANCE_IN_PROGRESS"


class ListAutonomousDatabasesInput(BaseModel):
    """Input for listing Autonomous Databases."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    compartment_id: str = Field(
        ...,
        description="Compartment OCID to list databases from",
        min_length=20
    )
    workload_type: ADBWorkloadType | None = Field(
        default=None,
        description="Filter by workload type: OLTP, DW, AJD, or APEX"
    )
    lifecycle_state: LifecycleState | None = Field(
        default=None,
        description="Filter by lifecycle state (e.g., AVAILABLE, STOPPED)"
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
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable, 'json' for machine-readable"
    )

    @field_validator('compartment_id')
    @classmethod
    def validate_compartment_ocid(cls, v: str) -> str:
        if not v.startswith('ocid1.'):
            raise ValueError("Invalid OCID format. Expected 'ocid1.*'")
        return v


class GetAutonomousDatabaseInput(BaseModel):
    """Input for getting a specific Autonomous Database."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    database_id: str = Field(
        ...,
        description="Autonomous Database OCID (e.g., 'ocid1.autonomousdatabase.oc1..aaaaaa')",
        min_length=20
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable, 'json' for machine-readable"
    )

    @field_validator('database_id')
    @classmethod
    def validate_database_ocid(cls, v: str) -> str:
        if not v.startswith('ocid1.autonomousdatabase.'):
            msg = "Invalid Autonomous Database OCID. Expected 'ocid1.autonomousdatabase.*'"
            raise ValueError(msg)
        return v


class StartAutonomousDatabaseInput(BaseModel):
    """Input for starting an Autonomous Database."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    database_id: str = Field(
        ...,
        description="Autonomous Database OCID to start",
        min_length=20
    )
    wait_for_state: bool = Field(
        default=False,
        description="Wait for the database to reach AVAILABLE state"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )

    @field_validator('database_id')
    @classmethod
    def validate_database_ocid(cls, v: str) -> str:
        if not v.startswith('ocid1.autonomousdatabase.'):
            raise ValueError("Invalid Autonomous Database OCID")
        return v


class StopAutonomousDatabaseInput(BaseModel):
    """Input for stopping an Autonomous Database."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    database_id: str = Field(
        ...,
        description="Autonomous Database OCID to stop",
        min_length=20
    )
    wait_for_state: bool = Field(
        default=False,
        description="Wait for the database to reach STOPPED state"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )

    @field_validator('database_id')
    @classmethod
    def validate_database_ocid(cls, v: str) -> str:
        if not v.startswith('ocid1.autonomousdatabase.'):
            raise ValueError("Invalid Autonomous Database OCID")
        return v


class GetDatabaseMetricsInput(BaseModel):
    """Input for getting database performance metrics."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    database_id: str = Field(
        ...,
        description="Database OCID (Autonomous or DB System)",
        min_length=20
    )
    metric_names: list[str] | None = Field(
        default=None,
        description="Specific metrics to retrieve (e.g., ['CpuUtilization', 'StorageUtilization'])"
    )
    hours_back: int = Field(
        default=24,
        description="Number of hours to look back for metrics",
        ge=1,
        le=168
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )


class ListDBSystemsInput(BaseModel):
    """Input for listing DB Systems."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    compartment_id: str = Field(
        ...,
        description="Compartment OCID to list DB Systems from",
        min_length=20
    )
    lifecycle_state: LifecycleState | None = Field(
        default=None,
        description="Filter by lifecycle state"
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
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )

    @field_validator('compartment_id')
    @classmethod
    def validate_compartment_ocid(cls, v: str) -> str:
        if not v.startswith('ocid1.'):
            raise ValueError("Invalid OCID format")
        return v


class ListBackupsInput(BaseModel):
    """Input for listing database backups."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    database_id: str | None = Field(
        default=None,
        description="Database OCID to list backups for"
    )
    compartment_id: str | None = Field(
        default=None,
        description="Compartment OCID (required if database_id not provided)"
    )
    database_type: DatabaseType = Field(
        default=DatabaseType.AUTONOMOUS,
        description="Type of database: autonomous, db_system, or mysql"
    )
    limit: int = Field(
        default=20,
        description="Maximum results to return",
        ge=1,
        le=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )


# Output models for structured responses
class AutonomousDatabaseSummary(BaseModel):
    """Summary of an Autonomous Database."""
    id: str
    display_name: str
    compartment_id: str
    lifecycle_state: str
    db_name: str
    db_workload: str
    cpu_core_count: int
    data_storage_size_in_tbs: int
    is_free_tier: bool
    time_created: str
    connection_strings: dict | None = None


class DBSystemSummary(BaseModel):
    """Summary of a DB System."""
    id: str
    display_name: str
    compartment_id: str
    lifecycle_state: str
    availability_domain: str
    shape: str
    cpu_core_count: int
    data_storage_size_in_gbs: int
    time_created: str
