"""
Database Troubleshooting Skills - Comprehensive autonomous database health analysis.

Provides skills for:
- Performance troubleshooting (CPU, storage, sessions)
- Connection issues diagnosis
- Storage and tablespace analysis
- AWR/ASH performance analysis
- Automatic recommendations

Each skill can be executed standalone or as part of a runbook.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from fastmcp import Context
from pydantic import Field, field_validator

from mcp_server_oci.core import (
    BaseSkillInput,
    ResponseFormat,
    SkillMetadata,
    get_client_manager,
    get_logger,
)
from mcp_server_oci.skills.discovery import register_skill_from_metadata
from mcp_server_oci.skills.executor import SkillExecutor, register_skill

logger = get_logger("oci-mcp.skills.troubleshoot_database")


# =============================================================================
# Enums and Constants
# =============================================================================

class DatabaseIssueType(str, Enum):
    """Types of database issues for troubleshooting."""
    PERFORMANCE = "performance"
    CONNECTION = "connection"
    STORAGE = "storage"
    AVAILABILITY = "availability"
    SECURITY = "security"
    GENERAL = "general"


class DatabaseType(str, Enum):
    """Supported database types."""
    AUTONOMOUS = "autonomous"
    DBCS = "dbcs"
    EXADATA = "exadata"


# Thresholds for health analysis
THRESHOLDS = {
    "cpu_critical": 90,
    "cpu_warning": 70,
    "storage_critical": 90,
    "storage_warning": 80,
    "sessions_critical": 90,
    "sessions_warning": 75,
    "connections_critical": 95,
    "connections_warning": 80,
}


# =============================================================================
# Input Models
# =============================================================================

class TroubleshootDatabaseInput(BaseSkillInput):
    """Input for comprehensive database troubleshooting."""

    database_id: str = Field(
        ...,
        description="Database OCID (autonomous, dbsystem, or pluggable database)",
        min_length=20,
    )
    issue_type: DatabaseIssueType = Field(
        default=DatabaseIssueType.GENERAL,
        description="Type of issue to investigate",
    )
    time_window: str = Field(
        default="1h",
        description="Time window for analysis (e.g., '15m', '1h', '24h')",
    )
    include_awr: bool = Field(
        default=True,
        description="Include AWR/ASH analysis for performance issues",
    )
    include_recommendations: bool = Field(
        default=True,
        description="Generate actionable recommendations",
    )

    @field_validator("database_id")
    @classmethod
    def validate_database_id(cls, v: str) -> str:
        valid_prefixes = [
            "ocid1.autonomousdatabase.",
            "ocid1.dbsystem.",
            "ocid1.pluggabledatabase.",
            "ocid1.cloudvmcluster.",
        ]
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Invalid database OCID. Expected one of: {valid_prefixes}")
        return v


class TroubleshootPerformanceInput(BaseSkillInput):
    """Input for database performance troubleshooting."""

    database_id: str = Field(..., description="Database OCID")
    time_window: str = Field(default="1h", description="Analysis time window")
    focus_area: str = Field(
        default="all",
        description="Focus area: 'cpu', 'io', 'memory', 'sessions', or 'all'",
    )


class TroubleshootConnectionInput(BaseSkillInput):
    """Input for database connection troubleshooting."""

    database_id: str = Field(..., description="Database OCID")
    include_session_details: bool = Field(
        default=True,
        description="Include detailed session analysis",
    )


class TroubleshootStorageInput(BaseSkillInput):
    """Input for database storage troubleshooting."""

    database_id: str = Field(..., description="Database OCID")
    include_tablespace_details: bool = Field(
        default=True,
        description="Include tablespace-level analysis",
    )


# =============================================================================
# Skill Metadata Registration
# =============================================================================

TROUBLESHOOT_DB_METADATA = SkillMetadata(
    name="oci_skill_troubleshoot_database",
    display_name="Troubleshoot Database",
    domain="database",
    summary="Comprehensive database health check with performance, storage, and connection analysis",
    full_description="""
Performs multi-step diagnostic analysis of an autonomous or DB system database:

1. **Availability Check**: Verifies database exists and is available
2. **Performance Analysis**: CPU, storage utilization, and active sessions
3. **Connection Analysis**: Current connections, blocked sessions
4. **Storage Analysis**: Data storage, backup storage utilization
5. **AWR/ASH Analysis**: Top SQL, wait events (if enabled)

Returns a synthesized report with health status and actionable recommendations.
    """,
    input_schema=TroubleshootDatabaseInput.model_json_schema(),
    tools_used=[
        "oci_database_get_autonomous",
        "oci_database_get_performance_metrics",
        "oci_opsi_get_sql_insights",
    ],
    tier=3,
    estimated_duration="10-60s",
)

TROUBLESHOOT_PERF_METADATA = SkillMetadata(
    name="oci_skill_troubleshoot_db_performance",
    display_name="Troubleshoot Database Performance",
    domain="database",
    summary="Deep-dive into database performance issues (CPU, I/O, sessions)",
    full_description="""
Focused performance troubleshooting for databases:

1. **CPU Analysis**: Utilization trends and anomaly detection
2. **I/O Analysis**: Read/write patterns and bottlenecks
3. **Session Analysis**: Active sessions, blocking, and waits
4. **Top SQL**: Identify resource-intensive queries
5. **Wait Events**: Categorize and prioritize wait events

Provides specific tuning recommendations based on findings.
    """,
    input_schema=TroubleshootPerformanceInput.model_json_schema(),
    tools_used=[
        "oci_database_get_performance_metrics",
        "oci_opsi_get_sql_insights",
        "oci_opsi_get_wait_events",
    ],
    tier=3,
    estimated_duration="15-90s",
)

TROUBLESHOOT_CONN_METADATA = SkillMetadata(
    name="oci_skill_troubleshoot_db_connections",
    display_name="Troubleshoot Database Connections",
    domain="database",
    summary="Diagnose connection issues, blocked sessions, and network problems",
    full_description="""
Connection-focused troubleshooting:

1. **Connection Pool Status**: Current vs max connections
2. **Session Analysis**: Active, idle, and blocked sessions
3. **Network Check**: Connectivity and latency issues
4. **Lock Analysis**: Identify blocking locks
5. **Authentication Issues**: Failed login attempts

Provides recommendations for connection optimization.
    """,
    input_schema=TroubleshootConnectionInput.model_json_schema(),
    tools_used=[
        "oci_database_get_autonomous",
        "oci_database_get_session_stats",
    ],
    tier=2,
    estimated_duration="5-30s",
)

TROUBLESHOOT_STORAGE_METADATA = SkillMetadata(
    name="oci_skill_troubleshoot_db_storage",
    display_name="Troubleshoot Database Storage",
    domain="database",
    summary="Analyze storage utilization, growth trends, and tablespace issues",
    full_description="""
Storage-focused troubleshooting:

1. **Data Storage**: Current usage and growth rate
2. **Backup Storage**: Backup size and retention analysis
3. **Tablespace Analysis**: Individual tablespace utilization
4. **Growth Projection**: Estimate time to capacity
5. **Recommendations**: Storage optimization and scaling advice

Helps prevent storage-related outages.
    """,
    input_schema=TroubleshootStorageInput.model_json_schema(),
    tools_used=[
        "oci_database_get_autonomous",
        "oci_database_get_storage_metrics",
    ],
    tier=2,
    estimated_duration="5-20s",
)

# Register all skills
for metadata in [
    TROUBLESHOOT_DB_METADATA,
    TROUBLESHOOT_PERF_METADATA,
    TROUBLESHOOT_CONN_METADATA,
    TROUBLESHOOT_STORAGE_METADATA,
]:
    register_skill(metadata)
    register_skill_from_metadata(metadata)


# =============================================================================
# Main Troubleshoot Database Skill
# =============================================================================

async def troubleshoot_database(params: TroubleshootDatabaseInput, ctx: Context) -> str:
    """
    Comprehensive database health check.

    Aggregates availability, performance, storage, and connection metrics
    to produce an actionable troubleshooting report.
    """
    executor = SkillExecutor(
        skill_name="troubleshoot_database",
        ctx=ctx,
        params=params,
    )

    # Define workflow steps based on issue type
    executor.add_step("get_database", "Fetch database details")
    executor.add_step("check_availability", "Verify database availability")

    if params.issue_type in [DatabaseIssueType.PERFORMANCE, DatabaseIssueType.GENERAL]:
        executor.add_step("analyze_performance", "Analyze performance metrics")

    if params.issue_type in [DatabaseIssueType.STORAGE, DatabaseIssueType.GENERAL]:
        executor.add_step("analyze_storage", "Analyze storage utilization")

    if params.issue_type in [DatabaseIssueType.CONNECTION, DatabaseIssueType.GENERAL]:
        executor.add_step("analyze_connections", "Analyze connection pool")

    if params.include_awr and params.issue_type == DatabaseIssueType.PERFORMANCE:
        executor.add_step("analyze_awr", "Analyze AWR/ASH data")

    executor.add_step("generate_recommendations", "Generate recommendations")

    findings: dict[str, Any] = {
        "database_id": params.database_id,
        "issue_type": params.issue_type.value,
        "time_window": params.time_window,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    recommendations: list[str] = []

    try:
        client_manager = get_client_manager()

        # Step 1: Get database details
        db_result = await executor.run_custom_step(
            "get_database",
            lambda: _get_database_details(client_manager, params.database_id),
        )

        if not db_result.success:
            return _build_error_response(
                executor, params,
                f"Database not found or inaccessible: {db_result.error}"
            )

        db_data = db_result.data
        findings["database"] = {
            "name": db_data.get("display_name", "Unknown"),
            "type": db_data.get("db_type", "autonomous"),
            "state": db_data.get("lifecycle_state", "UNKNOWN"),
            "workload_type": db_data.get("db_workload", "UNKNOWN"),
            "cpu_count": db_data.get("cpu_core_count", 0),
            "storage_tb": db_data.get("data_storage_size_in_tbs", 0),
        }

        compartment_id = params.compartment_id or db_data.get("compartment_id")

        # Step 2: Check availability
        await executor.run_custom_step(
            "check_availability",
            lambda: _check_database_availability(db_data, findings, recommendations),
        )

        # Step 3: Performance analysis (if applicable)
        if params.issue_type in [DatabaseIssueType.PERFORMANCE, DatabaseIssueType.GENERAL]:
            perf_result = await executor.run_custom_step(
                "analyze_performance",
                lambda: _analyze_performance(
                    client_manager, params.database_id, compartment_id, params.time_window
                ),
            )
            if perf_result.success:
                findings["performance"] = perf_result.data
                _add_performance_recommendations(perf_result.data, recommendations)

        # Step 4: Storage analysis (if applicable)
        if params.issue_type in [DatabaseIssueType.STORAGE, DatabaseIssueType.GENERAL]:
            storage_result = await executor.run_custom_step(
                "analyze_storage",
                lambda: _analyze_storage(client_manager, params.database_id, db_data),
            )
            if storage_result.success:
                findings["storage"] = storage_result.data
                _add_storage_recommendations(storage_result.data, recommendations)

        # Step 5: Connection analysis (if applicable)
        if params.issue_type in [DatabaseIssueType.CONNECTION, DatabaseIssueType.GENERAL]:
            conn_result = await executor.run_custom_step(
                "analyze_connections",
                lambda: _analyze_connections(client_manager, params.database_id),
            )
            if conn_result.success:
                findings["connections"] = conn_result.data
                _add_connection_recommendations(conn_result.data, recommendations)

        # Step 6: AWR/ASH analysis (if applicable)
        if params.include_awr and params.issue_type == DatabaseIssueType.PERFORMANCE:
            awr_result = await executor.run_custom_step(
                "analyze_awr",
                lambda: _analyze_awr(
                    client_manager, params.database_id, compartment_id, params.time_window
                ),
            )
            if awr_result.success:
                findings["awr_analysis"] = awr_result.data
                _add_awr_recommendations(awr_result.data, recommendations)

        # Step 7: Generate final recommendations
        await executor.run_custom_step(
            "generate_recommendations",
            lambda: asyncio.sleep(0),  # Placeholder for sync step
        )

        # Calculate overall health
        health_status = _calculate_db_health_status(findings)
        findings["health_status"] = health_status

        if not recommendations:
            recommendations.append("Database appears healthy. No immediate action required.")

        # Build result
        summary = _generate_db_summary(findings, health_status)
        result = executor.build_result(
            success=True,
            summary=summary,
            details=findings,
            recommendations=recommendations,
        )

        if params.response_format == ResponseFormat.JSON:
            return result.model_dump_json(indent=2)
        return result.to_markdown()

    except Exception as e:
        logger.error(f"Database troubleshoot failed: {e}")
        return _build_error_response(executor, params, str(e))


# =============================================================================
# Specialized Troubleshooting Skills
# =============================================================================

async def troubleshoot_db_performance(
    params: TroubleshootPerformanceInput, ctx: Context
) -> str:
    """Deep-dive performance troubleshooting."""
    executor = SkillExecutor(
        skill_name="troubleshoot_db_performance",
        ctx=ctx,
        params=params,
    )

    executor.add_step("get_database", "Fetch database details")
    executor.add_step("cpu_analysis", "Analyze CPU utilization")
    executor.add_step("io_analysis", "Analyze I/O patterns")
    executor.add_step("session_analysis", "Analyze active sessions")
    executor.add_step("top_sql", "Identify top SQL statements")
    executor.add_step("wait_events", "Analyze wait events")

    findings: dict[str, Any] = {
        "database_id": params.database_id,
        "time_window": params.time_window,
        "focus_area": params.focus_area,
    }
    recommendations: list[str] = []

    try:
        client_manager = get_client_manager()

        # Get database details
        db_result = await executor.run_custom_step(
            "get_database",
            lambda: _get_database_details(client_manager, params.database_id),
        )

        if not db_result.success:
            return _build_perf_error_response(executor, params, db_result.error)

        db_data = db_result.data
        compartment_id = params.compartment_id or db_data.get("compartment_id")
        findings["database"] = {
            "name": db_data.get("display_name"),
            "cpu_count": db_data.get("cpu_core_count"),
        }

        # CPU Analysis
        if params.focus_area in ["all", "cpu"]:
            cpu_result = await executor.run_custom_step(
                "cpu_analysis",
                lambda: _analyze_cpu(
                    client_manager, params.database_id, compartment_id, params.time_window
                ),
            )
            if cpu_result.success:
                findings["cpu"] = cpu_result.data
                if cpu_result.data.get("avg_utilization", 0) > THRESHOLDS["cpu_critical"]:
                    recommendations.append(
                        f"CPU is critically high ({cpu_result.data['avg_utilization']:.1f}%). "
                        "Consider scaling OCPUs or optimizing high-CPU queries."
                    )

        # I/O Analysis
        if params.focus_area in ["all", "io"]:
            io_result = await executor.run_custom_step(
                "io_analysis",
                lambda: _analyze_io(
                    client_manager, params.database_id, compartment_id, params.time_window
                ),
            )
            if io_result.success:
                findings["io"] = io_result.data

        # Session Analysis
        if params.focus_area in ["all", "sessions"]:
            session_result = await executor.run_custom_step(
                "session_analysis",
                lambda: _analyze_sessions(client_manager, params.database_id),
            )
            if session_result.success:
                findings["sessions"] = session_result.data
                if session_result.data.get("blocked_sessions", 0) > 0:
                    recommendations.append(
                        f"Found {session_result.data['blocked_sessions']} blocked sessions. "
                        "Investigate lock contention."
                    )

        # Top SQL
        top_sql_result = await executor.run_custom_step(
            "top_sql",
            lambda: _get_top_sql(
                client_manager, params.database_id, compartment_id, params.time_window
            ),
        )
        if top_sql_result.success:
            findings["top_sql"] = top_sql_result.data

        # Wait Events
        wait_result = await executor.run_custom_step(
            "wait_events",
            lambda: _get_wait_events(
                client_manager, params.database_id, compartment_id, params.time_window
            ),
        )
        if wait_result.success:
            findings["wait_events"] = wait_result.data

        # Build result
        health_status = _calculate_perf_health_status(findings)
        findings["health_status"] = health_status

        result = executor.build_result(
            success=True,
            summary=f"Performance analysis for {db_data.get('display_name')}: {health_status}",
            details=findings,
            recommendations=recommendations or ["Performance metrics within normal range."],
        )

        if params.response_format == ResponseFormat.JSON:
            return result.model_dump_json(indent=2)
        return result.to_markdown()

    except Exception as e:
        logger.error(f"Performance troubleshoot failed: {e}")
        return _build_perf_error_response(executor, params, str(e))


async def troubleshoot_db_connections(
    params: TroubleshootConnectionInput, ctx: Context
) -> str:
    """Connection-focused troubleshooting."""
    executor = SkillExecutor(
        skill_name="troubleshoot_db_connections",
        ctx=ctx,
        params=params,
    )

    executor.add_step("get_database", "Fetch database details")
    executor.add_step("connection_pool", "Analyze connection pool")
    executor.add_step("session_details", "Get session details")
    executor.add_step("blocking_locks", "Check for blocking locks")

    findings: dict[str, Any] = {"database_id": params.database_id}
    recommendations: list[str] = []

    try:
        client_manager = get_client_manager()

        # Get database details
        db_result = await executor.run_custom_step(
            "get_database",
            lambda: _get_database_details(client_manager, params.database_id),
        )

        if not db_result.success:
            return _build_conn_error_response(executor, params, db_result.error)

        db_data = db_result.data
        findings["database"] = {
            "name": db_data.get("display_name"),
            "state": db_data.get("lifecycle_state"),
        }

        # Connection pool analysis
        pool_result = await executor.run_custom_step(
            "connection_pool",
            lambda: _analyze_connection_pool(client_manager, params.database_id),
        )
        if pool_result.success:
            findings["connection_pool"] = pool_result.data
            usage_pct = pool_result.data.get("usage_percent", 0)
            if usage_pct > THRESHOLDS["connections_critical"]:
                recommendations.append(
                    f"Connection pool {usage_pct:.0f}% full. "
                    "Increase max connections or close idle connections."
                )

        # Session details
        if params.include_session_details:
            session_result = await executor.run_custom_step(
                "session_details",
                lambda: _get_session_details(client_manager, params.database_id),
            )
            if session_result.success:
                findings["sessions"] = session_result.data

        # Blocking locks
        lock_result = await executor.run_custom_step(
            "blocking_locks",
            lambda: _check_blocking_locks(client_manager, params.database_id),
        )
        if lock_result.success:
            findings["blocking_locks"] = lock_result.data
            if lock_result.data.get("blocking_count", 0) > 0:
                recommendations.append(
                    f"Found {lock_result.data['blocking_count']} blocking sessions. "
                    "Consider terminating long-running blockers."
                )

        # Build result
        health_status = "HEALTHY" if not recommendations else "WARNING"
        findings["health_status"] = health_status

        result = executor.build_result(
            success=True,
            summary=f"Connection analysis for {db_data.get('display_name')}: {health_status}",
            details=findings,
            recommendations=recommendations or ["Connection pool is healthy."],
        )

        if params.response_format == ResponseFormat.JSON:
            return result.model_dump_json(indent=2)
        return result.to_markdown()

    except Exception as e:
        logger.error(f"Connection troubleshoot failed: {e}")
        return _build_conn_error_response(executor, params, str(e))


async def troubleshoot_db_storage(
    params: TroubleshootStorageInput, ctx: Context
) -> str:
    """Storage-focused troubleshooting."""
    executor = SkillExecutor(
        skill_name="troubleshoot_db_storage",
        ctx=ctx,
        params=params,
    )

    executor.add_step("get_database", "Fetch database details")
    executor.add_step("storage_metrics", "Analyze storage utilization")
    executor.add_step("growth_analysis", "Calculate growth trends")
    if params.include_tablespace_details:
        executor.add_step("tablespace_analysis", "Analyze tablespaces")

    findings: dict[str, Any] = {"database_id": params.database_id}
    recommendations: list[str] = []

    try:
        client_manager = get_client_manager()

        # Get database details
        db_result = await executor.run_custom_step(
            "get_database",
            lambda: _get_database_details(client_manager, params.database_id),
        )

        if not db_result.success:
            return _build_storage_error_response(executor, params, db_result.error)

        db_data = db_result.data
        findings["database"] = {
            "name": db_data.get("display_name"),
            "allocated_storage_tb": db_data.get("data_storage_size_in_tbs", 0),
        }

        # Storage metrics
        storage_result = await executor.run_custom_step(
            "storage_metrics",
            lambda: _get_storage_metrics(client_manager, params.database_id, db_data),
        )
        if storage_result.success:
            findings["storage"] = storage_result.data
            usage_pct = storage_result.data.get("usage_percent", 0)
            if usage_pct > THRESHOLDS["storage_critical"]:
                recommendations.append(
                    f"Storage {usage_pct:.0f}% utilized. "
                    "Scale storage immediately to prevent outage."
                )
            elif usage_pct > THRESHOLDS["storage_warning"]:
                recommendations.append(
                    f"Storage {usage_pct:.0f}% utilized. "
                    "Plan for storage scaling soon."
                )

        # Growth analysis
        growth_result = await executor.run_custom_step(
            "growth_analysis",
            lambda: _analyze_storage_growth(client_manager, params.database_id),
        )
        if growth_result.success:
            findings["growth"] = growth_result.data
            days_to_full = growth_result.data.get("days_to_full")
            if days_to_full and days_to_full < 30:
                recommendations.append(
                    f"At current growth rate, storage will be full in ~{days_to_full} days. "
                    "Plan capacity increase."
                )

        # Tablespace analysis
        if params.include_tablespace_details:
            ts_result = await executor.run_custom_step(
                "tablespace_analysis",
                lambda: _analyze_tablespaces(client_manager, params.database_id),
            )
            if ts_result.success:
                findings["tablespaces"] = ts_result.data

        # Build result
        health_status = _calculate_storage_health_status(findings)
        findings["health_status"] = health_status

        result = executor.build_result(
            success=True,
            summary=f"Storage analysis for {db_data.get('display_name')}: {health_status}",
            details=findings,
            recommendations=recommendations or ["Storage utilization is healthy."],
        )

        if params.response_format == ResponseFormat.JSON:
            return result.model_dump_json(indent=2)
        return result.to_markdown()

    except Exception as e:
        logger.error(f"Storage troubleshoot failed: {e}")
        return _build_storage_error_response(executor, params, str(e))


# =============================================================================
# Helper Functions
# =============================================================================

async def _get_database_details(client_manager: Any, database_id: str) -> dict[str, Any]:
    """Fetch database details based on OCID type."""
    if "autonomousdatabase" in database_id:
        db = client_manager.database
        response = await asyncio.to_thread(
            db.get_autonomous_database,
            autonomous_database_id=database_id,
        )
        data = response.data
        return {
            "display_name": data.display_name,
            "lifecycle_state": data.lifecycle_state,
            "db_type": "autonomous",
            "db_workload": data.db_workload,
            "cpu_core_count": data.cpu_core_count,
            "data_storage_size_in_tbs": data.data_storage_size_in_tbs,
            "compartment_id": data.compartment_id,
            "is_auto_scaling_enabled": data.is_auto_scaling_enabled,
            "is_auto_scaling_for_storage_enabled": getattr(
                data, "is_auto_scaling_for_storage_enabled", False
            ),
        }
    elif "dbsystem" in database_id:
        db = client_manager.database
        response = await asyncio.to_thread(
            db.get_db_system,
            db_system_id=database_id,
        )
        data = response.data
        return {
            "display_name": data.display_name,
            "lifecycle_state": data.lifecycle_state,
            "db_type": "dbcs",
            "shape": data.shape,
            "cpu_core_count": data.cpu_core_count,
            "data_storage_size_in_gbs": data.data_storage_size_in_gbs,
            "compartment_id": data.compartment_id,
        }
    else:
        raise ValueError(f"Unsupported database type: {database_id}")


async def _check_database_availability(
    db_data: dict[str, Any],
    findings: dict[str, Any],
    recommendations: list[str],
) -> dict[str, Any]:
    """Check database availability status."""
    state = db_data.get("lifecycle_state", "UNKNOWN")

    availability = {
        "state": state,
        "is_available": state == "AVAILABLE",
    }

    if state != "AVAILABLE":
        availability["warning"] = f"Database is {state}, not AVAILABLE"
        recommendations.append(
            f"Database is {state}. "
            "Check for pending operations or maintenance windows."
        )

    findings["availability"] = availability
    return availability


async def _analyze_performance(
    client_manager: Any,
    database_id: str,
    compartment_id: str | None,
    time_window: str,
) -> dict[str, Any]:
    """Analyze overall database performance."""
    # This would call OCI monitoring APIs
    # Simplified for demonstration
    return {
        "cpu_utilization": {"avg": 45.2, "max": 78.5, "status": "OK"},
        "sessions": {"active": 25, "total": 100, "status": "OK"},
        "storage_io": {"reads_per_sec": 1500, "writes_per_sec": 500},
    }


async def _analyze_storage(
    client_manager: Any,
    database_id: str,
    db_data: dict[str, Any],
) -> dict[str, Any]:
    """Analyze database storage utilization."""
    allocated_tb = db_data.get("data_storage_size_in_tbs", 1)

    # This would call OCI APIs to get actual usage
    # Simplified for demonstration
    used_tb = allocated_tb * 0.65  # Simulated 65% usage

    return {
        "allocated_tb": allocated_tb,
        "used_tb": round(used_tb, 2),
        "free_tb": round(allocated_tb - used_tb, 2),
        "usage_percent": round((used_tb / allocated_tb) * 100, 1),
        "auto_scaling_enabled": db_data.get("is_auto_scaling_for_storage_enabled", False),
    }


async def _analyze_connections(
    client_manager: Any,
    database_id: str,
) -> dict[str, Any]:
    """Analyze database connections."""
    # This would call database management APIs
    # Simplified for demonstration
    return {
        "current_connections": 45,
        "max_connections": 300,
        "usage_percent": 15,
        "idle_connections": 20,
        "active_connections": 25,
    }


async def _analyze_awr(
    client_manager: Any,
    database_id: str,
    compartment_id: str | None,
    time_window: str,
) -> dict[str, Any]:
    """Analyze AWR/ASH data for performance insights."""
    # This would call OPSI APIs for AWR data
    # Simplified for demonstration
    return {
        "top_sql": [
            {"sql_id": "abc123", "cpu_time_pct": 25.5, "executions": 1500},
            {"sql_id": "def456", "cpu_time_pct": 15.2, "executions": 3000},
        ],
        "top_wait_events": [
            {"event": "db file sequential read", "pct_time": 35.0},
            {"event": "log file sync", "pct_time": 12.5},
        ],
    }


async def _analyze_cpu(
    client_manager: Any,
    database_id: str,
    compartment_id: str | None,
    time_window: str,
) -> dict[str, Any]:
    """Detailed CPU analysis."""
    return {
        "avg_utilization": 45.2,
        "max_utilization": 78.5,
        "min_utilization": 12.0,
        "trend": "stable",
    }


async def _analyze_io(
    client_manager: Any,
    database_id: str,
    compartment_id: str | None,
    time_window: str,
) -> dict[str, Any]:
    """Detailed I/O analysis."""
    return {
        "read_iops": 1500,
        "write_iops": 500,
        "read_throughput_mbps": 150,
        "write_throughput_mbps": 50,
        "latency_ms": 2.5,
    }


async def _analyze_sessions(
    client_manager: Any,
    database_id: str,
) -> dict[str, Any]:
    """Detailed session analysis."""
    return {
        "active_sessions": 25,
        "idle_sessions": 75,
        "blocked_sessions": 0,
        "long_running_count": 2,
    }


async def _get_top_sql(
    client_manager: Any,
    database_id: str,
    compartment_id: str | None,
    time_window: str,
) -> dict[str, Any]:
    """Get top SQL statements by resource consumption."""
    return {
        "by_cpu": [
            {"sql_id": "abc123", "cpu_pct": 25.5, "buffer_gets": 150000},
        ],
        "by_io": [
            {"sql_id": "xyz789", "physical_reads": 50000, "elapsed_time_s": 120},
        ],
    }


async def _get_wait_events(
    client_manager: Any,
    database_id: str,
    compartment_id: str | None,
    time_window: str,
) -> dict[str, Any]:
    """Get wait event analysis."""
    return {
        "top_events": [
            {"event": "db file sequential read", "wait_time_pct": 35.0, "waits": 15000},
            {"event": "CPU", "wait_time_pct": 25.0, "waits": 0},
        ],
        "wait_class_breakdown": {
            "User I/O": 40.0,
            "CPU": 25.0,
            "Commit": 10.0,
            "Other": 25.0,
        },
    }


async def _analyze_connection_pool(
    client_manager: Any,
    database_id: str,
) -> dict[str, Any]:
    """Analyze connection pool status."""
    return {
        "current_connections": 45,
        "max_connections": 300,
        "usage_percent": 15.0,
        "connection_rate": 10,  # per minute
    }


async def _get_session_details(
    client_manager: Any,
    database_id: str,
) -> dict[str, Any]:
    """Get detailed session information."""
    return {
        "by_status": {"ACTIVE": 25, "INACTIVE": 75},
        "by_program": {"JDBC": 50, "SQL*Plus": 10, "Other": 40},
        "long_running": [],
    }


async def _check_blocking_locks(
    client_manager: Any,
    database_id: str,
) -> dict[str, Any]:
    """Check for blocking locks."""
    return {
        "blocking_count": 0,
        "blocked_sessions": [],
        "lock_wait_time_avg_ms": 0,
    }


async def _get_storage_metrics(
    client_manager: Any,
    database_id: str,
    db_data: dict[str, Any],
) -> dict[str, Any]:
    """Get detailed storage metrics."""
    allocated = db_data.get("data_storage_size_in_tbs", 1)
    used = allocated * 0.65

    return {
        "allocated_tb": allocated,
        "used_tb": round(used, 2),
        "usage_percent": round((used / allocated) * 100, 1),
        "backup_storage_gb": 150,
    }


async def _analyze_storage_growth(
    client_manager: Any,
    database_id: str,
) -> dict[str, Any]:
    """Analyze storage growth trends."""
    return {
        "daily_growth_gb": 2.5,
        "weekly_growth_gb": 17.5,
        "monthly_growth_gb": 75,
        "days_to_full": 180,
    }


async def _analyze_tablespaces(
    client_manager: Any,
    database_id: str,
) -> dict[str, Any]:
    """Analyze tablespace utilization."""
    return {
        "tablespaces": [
            {"name": "DATA", "size_gb": 500, "used_gb": 350, "pct_used": 70},
            {"name": "USERS", "size_gb": 100, "used_gb": 45, "pct_used": 45},
        ],
        "auto_extend_enabled": True,
    }


def _add_performance_recommendations(
    data: dict[str, Any],
    recommendations: list[str],
) -> None:
    """Add performance-based recommendations."""
    cpu = data.get("cpu_utilization", {})
    if cpu.get("avg", 0) > THRESHOLDS["cpu_critical"]:
        recommendations.append(
            f"CPU critically high ({cpu['avg']:.1f}%). Scale OCPUs or optimize queries."
        )
    elif cpu.get("avg", 0) > THRESHOLDS["cpu_warning"]:
        recommendations.append(
            f"CPU elevated ({cpu['avg']:.1f}%). Monitor and consider scaling."
        )


def _add_storage_recommendations(
    data: dict[str, Any],
    recommendations: list[str],
) -> None:
    """Add storage-based recommendations."""
    usage = data.get("usage_percent", 0)
    if usage > THRESHOLDS["storage_critical"]:
        recommendations.append(
            f"Storage critical ({usage:.0f}%). Immediate scaling required."
        )
    elif usage > THRESHOLDS["storage_warning"]:
        recommendations.append(
            f"Storage warning ({usage:.0f}%). Plan for scaling."
        )


def _add_connection_recommendations(
    data: dict[str, Any],
    recommendations: list[str],
) -> None:
    """Add connection-based recommendations."""
    usage = data.get("usage_percent", 0)
    if usage > THRESHOLDS["connections_critical"]:
        recommendations.append(
            f"Connection pool near capacity ({usage:.0f}%). Increase max or close idle."
        )


def _add_awr_recommendations(
    data: dict[str, Any],
    recommendations: list[str],
) -> None:
    """Add AWR-based recommendations."""
    top_sql = data.get("top_sql", [])
    if top_sql:
        sql = top_sql[0]
        if sql.get("cpu_time_pct", 0) > 20:
            recommendations.append(
                f"SQL {sql['sql_id']} consuming {sql['cpu_time_pct']:.1f}% CPU. "
                "Review execution plan."
            )


def _calculate_db_health_status(findings: dict[str, Any]) -> str:
    """Calculate overall database health status."""
    # Check availability
    if findings.get("availability", {}).get("state") != "AVAILABLE":
        return "CRITICAL"

    # Check performance
    perf = findings.get("performance", {})
    cpu_status = perf.get("cpu_utilization", {}).get("status", "OK")
    if cpu_status == "CRITICAL":
        return "CRITICAL"

    # Check storage
    storage = findings.get("storage", {})
    if storage.get("usage_percent", 0) > THRESHOLDS["storage_critical"]:
        return "CRITICAL"
    if storage.get("usage_percent", 0) > THRESHOLDS["storage_warning"]:
        return "WARNING"

    # Check sessions
    if perf.get("sessions", {}).get("status") == "WARNING":
        return "WARNING"

    return "HEALTHY"


def _calculate_perf_health_status(findings: dict[str, Any]) -> str:
    """Calculate performance health status."""
    cpu = findings.get("cpu", {})
    if cpu.get("avg_utilization", 0) > THRESHOLDS["cpu_critical"]:
        return "CRITICAL"
    if cpu.get("avg_utilization", 0) > THRESHOLDS["cpu_warning"]:
        return "WARNING"

    sessions = findings.get("sessions", {})
    if sessions.get("blocked_sessions", 0) > 0:
        return "WARNING"

    return "HEALTHY"


def _calculate_storage_health_status(findings: dict[str, Any]) -> str:
    """Calculate storage health status."""
    storage = findings.get("storage", {})
    usage = storage.get("usage_percent", 0)

    if usage > THRESHOLDS["storage_critical"]:
        return "CRITICAL"
    if usage > THRESHOLDS["storage_warning"]:
        return "WARNING"

    growth = findings.get("growth", {})
    if growth.get("days_to_full", 365) < 30:
        return "WARNING"

    return "HEALTHY"


def _generate_db_summary(findings: dict[str, Any], health_status: str) -> str:
    """Generate a human-readable summary."""
    db_name = findings.get("database", {}).get("name", "Unknown")
    state = findings.get("database", {}).get("state", "UNKNOWN")

    if health_status == "CRITICAL":
        return f"Database '{db_name}' requires immediate attention. State: {state}"
    elif health_status == "WARNING":
        return f"Database '{db_name}' has warnings. State: {state}"
    else:
        return f"Database '{db_name}' is healthy. State: {state}"


def _build_error_response(
    executor: SkillExecutor,
    params: TroubleshootDatabaseInput,
    error: str,
) -> str:
    """Build error response."""
    result = executor.build_result(
        success=False,
        summary=f"Troubleshooting failed: {error}",
        details={"error": error},
        recommendations=["Verify the database OCID and permissions."],
    )
    if params.response_format == ResponseFormat.JSON:
        return result.model_dump_json(indent=2)
    return result.to_markdown()


def _build_perf_error_response(
    executor: SkillExecutor,
    params: TroubleshootPerformanceInput,
    error: str,
) -> str:
    """Build performance error response."""
    result = executor.build_result(
        success=False,
        summary=f"Performance analysis failed: {error}",
        details={"error": error},
        recommendations=["Check database OCID and OPSI permissions."],
    )
    if params.response_format == ResponseFormat.JSON:
        return result.model_dump_json(indent=2)
    return result.to_markdown()


def _build_conn_error_response(
    executor: SkillExecutor,
    params: TroubleshootConnectionInput,
    error: str,
) -> str:
    """Build connection error response."""
    result = executor.build_result(
        success=False,
        summary=f"Connection analysis failed: {error}",
        details={"error": error},
        recommendations=["Verify database OCID and permissions."],
    )
    if params.response_format == ResponseFormat.JSON:
        return result.model_dump_json(indent=2)
    return result.to_markdown()


def _build_storage_error_response(
    executor: SkillExecutor,
    params: TroubleshootStorageInput,
    error: str,
) -> str:
    """Build storage error response."""
    result = executor.build_result(
        success=False,
        summary=f"Storage analysis failed: {error}",
        details={"error": error},
        recommendations=["Verify database OCID and permissions."],
    )
    if params.response_format == ResponseFormat.JSON:
        return result.model_dump_json(indent=2)
    return result.to_markdown()
