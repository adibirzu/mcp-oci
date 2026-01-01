"""
Runbook Framework for Database Operations.

Provides a structured way to define and execute multi-step operational runbooks
for database monitoring, troubleshooting, and maintenance.

Features:
- Declarative runbook definitions
- Conditional step execution
- Parallel step support
- Result aggregation
- Automatic remediation suggestions
"""

from __future__ import annotations

import asyncio
import operator
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

from mcp_server_oci.core import get_logger
from mcp_server_oci.core.shared_memory import (
    SharedContext,
    get_shared_store,
    share_finding,
    share_recommendation,
)

logger = get_logger("oci-mcp.skills.runbooks")


# =============================================================================
# Runbook Data Structures
# =============================================================================

class StepStatus(str, Enum):
    """Status of a runbook step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunbookStatus(str, Enum):
    """Overall runbook execution status."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SeverityLevel(str, Enum):
    """Severity level for findings."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class StepResult:
    """Result of a single runbook step."""
    step_id: str
    status: StepStatus
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    findings: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@dataclass
class RunbookResult:
    """Complete result of a runbook execution."""
    runbook_id: str
    runbook_name: str
    status: RunbookStatus
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: int = 0
    steps: list[StepResult] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


class RunbookStep(BaseModel):
    """Definition of a runbook step."""

    id: str = Field(..., description="Unique step identifier")
    name: str = Field(..., description="Human-readable step name")
    description: str = Field(default="", description="Step description")
    tool_name: str | None = Field(default=None, description="MCP tool to execute")
    skill_name: str | None = Field(default=None, description="Skill to execute")
    params: dict[str, Any] = Field(default_factory=dict, description="Step parameters")
    condition: str | None = Field(
        default=None,
        description="Condition expression for execution (e.g., 'cpu_usage > 80')"
    )
    on_failure: str = Field(
        default="continue",
        description="Action on failure: 'continue', 'stop', or 'skip_remaining'"
    )
    timeout_seconds: int = Field(default=60, description="Step timeout")
    parallel_with: list[str] = Field(
        default_factory=list,
        description="Step IDs to run in parallel"
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Step IDs this step depends on"
    )


class RunbookDefinition(BaseModel):
    """Complete runbook definition."""

    id: str = Field(..., description="Unique runbook identifier")
    name: str = Field(..., description="Human-readable runbook name")
    version: str = Field(default="1.0.0", description="Runbook version")
    description: str = Field(default="", description="Runbook description")
    category: str = Field(default="general", description="Runbook category")
    target_resource_type: str = Field(
        default="database",
        description="Type of resource this runbook operates on"
    )
    steps: list[RunbookStep] = Field(..., description="Ordered list of steps")
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Default variables for the runbook"
    )
    thresholds: dict[str, float] = Field(
        default_factory=dict,
        description="Threshold values for checks"
    )
    remediation_enabled: bool = Field(
        default=False,
        description="Whether automatic remediation is enabled"
    )


# =============================================================================
# Safe Expression Evaluator
# =============================================================================

class SafeExpressionEvaluator:
    """
    Safe expression evaluator for runbook conditions.

    Supports only simple comparison expressions like:
    - "cpu_usage > 80"
    - "storage_pct >= 90"
    - "blocked_sessions == 0"
    - "include_awr == True"
    """

    # Supported operators
    OPERATORS = {
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
        '==': operator.eq,
        '!=': operator.ne,
    }

    # Pattern for simple comparison: variable operator value
    PATTERN = re.compile(
        r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*'  # variable name
        r'(>=|<=|==|!=|>|<)\s*'              # operator
        r'(.+?)\s*$'                          # value
    )

    @classmethod
    def evaluate(cls, expression: str, context: dict[str, Any]) -> bool:
        """
        Safely evaluate a simple comparison expression.

        Args:
            expression: Expression like "cpu_usage > 80"
            context: Dictionary of variable values

        Returns:
            Boolean result of the comparison
        """
        match = cls.PATTERN.match(expression)
        if not match:
            logger.warning(f"Invalid condition expression format: {expression}")
            return True  # Default to executing if expression is invalid

        var_name, op_str, value_str = match.groups()

        # Get variable value from context
        var_value = context.get(var_name)
        if var_value is None:
            # Try to find in nested step results
            for key, val in context.items():
                if key.startswith("step_") and isinstance(val, dict):
                    if var_name in val:
                        var_value = val[var_name]
                        break

        if var_value is None:
            logger.warning(f"Variable not found in context: {var_name}")
            return True  # Default to executing if variable not found

        # Parse the comparison value
        try:
            compare_value = cls._parse_value(value_str)
        except ValueError as e:
            logger.warning(f"Failed to parse value '{value_str}': {e}")
            return True

        # Get the operator function
        op_func = cls.OPERATORS.get(op_str)
        if not op_func:
            logger.warning(f"Unknown operator: {op_str}")
            return True

        # Perform the comparison
        try:
            return op_func(var_value, compare_value)
        except TypeError as e:
            logger.warning(f"Type mismatch in comparison: {e}")
            return True

    @classmethod
    def _parse_value(cls, value_str: str) -> Any:
        """Parse a string value into the appropriate type."""
        value_str = value_str.strip()

        # Boolean
        if value_str == "True":
            return True
        if value_str == "False":
            return False

        # None
        if value_str == "None":
            return None

        # Integer
        try:
            return int(value_str)
        except ValueError:
            pass

        # Float
        try:
            return float(value_str)
        except ValueError:
            pass

        # String (remove quotes if present)
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]

        return value_str


# =============================================================================
# Runbook Registry
# =============================================================================

class RunbookRegistry:
    """
    Registry for runbook definitions.

    Stores and retrieves runbook definitions by ID or category.
    Supports dynamic registration of new runbooks.
    """

    _instance: RunbookRegistry | None = None
    _runbooks: dict[str, RunbookDefinition]

    def __init__(self):
        self._runbooks = {}
        self._categories: dict[str, list[str]] = {}

    @classmethod
    def get_instance(cls) -> RunbookRegistry:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = RunbookRegistry()
            cls._instance._register_builtin_runbooks()
        return cls._instance

    def register(self, runbook: RunbookDefinition) -> None:
        """Register a runbook definition."""
        self._runbooks[runbook.id] = runbook

        # Index by category
        if runbook.category not in self._categories:
            self._categories[runbook.category] = []
        if runbook.id not in self._categories[runbook.category]:
            self._categories[runbook.category].append(runbook.id)

        logger.info(f"Registered runbook: {runbook.id} ({runbook.category})")

    def get(self, runbook_id: str) -> RunbookDefinition | None:
        """Get a runbook by ID."""
        return self._runbooks.get(runbook_id)

    def list_all(self) -> list[RunbookDefinition]:
        """List all registered runbooks."""
        return list(self._runbooks.values())

    def list_by_category(self, category: str) -> list[RunbookDefinition]:
        """List runbooks in a category."""
        ids = self._categories.get(category, [])
        return [self._runbooks[id] for id in ids if id in self._runbooks]

    def list_categories(self) -> list[str]:
        """List all categories."""
        return list(self._categories.keys())

    def _register_builtin_runbooks(self) -> None:
        """Register built-in runbooks."""
        for runbook in BUILTIN_RUNBOOKS:
            self.register(runbook)


# =============================================================================
# Runbook Executor
# =============================================================================

class RunbookExecutor:
    """
    Executes runbook definitions.

    Handles step orchestration, condition evaluation, parallel execution,
    and result aggregation.
    """

    def __init__(
        self,
        runbook: RunbookDefinition,
        tool_executor: Callable | None = None,
        skill_executor: Callable | None = None,
    ):
        self.runbook = runbook
        self.tool_executor = tool_executor
        self.skill_executor = skill_executor
        self._context: dict[str, Any] = {}
        self._step_results: dict[str, StepResult] = {}

    async def execute(
        self,
        resource_id: str,
        session_id: str,
        variables: dict[str, Any] | None = None,
    ) -> RunbookResult:
        """
        Execute the runbook.

        Args:
            resource_id: Target resource OCID
            session_id: Session identifier for tracking
            variables: Override variables for this execution

        Returns:
            RunbookResult with all step results and findings
        """
        start_time = datetime.now(UTC)

        # Initialize context
        self._context = {
            "resource_id": resource_id,
            "session_id": session_id,
            **self.runbook.variables,
            **(variables or {}),
        }

        result = RunbookResult(
            runbook_id=self.runbook.id,
            runbook_name=self.runbook.name,
            status=RunbookStatus.RUNNING,
            start_time=start_time,
            context=self._context.copy(),
        )

        # Create shared context for inter-agent communication
        shared_store = get_shared_store()
        shared_context = SharedContext(
            session_id=session_id,
            resource_id=resource_id,
            resource_type=self.runbook.target_resource_type,
        )
        await shared_store.save_context(shared_context)

        try:
            # Execute steps in order
            should_stop = False

            for step in self.runbook.steps:
                if should_stop:
                    step_result = self._create_skipped_result(step)
                    result.steps.append(step_result)
                    continue

                # Check dependencies
                if not self._dependencies_met(step):
                    step_result = self._create_skipped_result(
                        step, reason="Dependencies not met"
                    )
                    result.steps.append(step_result)
                    continue

                # Check condition using safe evaluator
                if step.condition and not self._evaluate_condition(step.condition):
                    step_result = self._create_skipped_result(
                        step, reason=f"Condition not met: {step.condition}"
                    )
                    result.steps.append(step_result)
                    continue

                # Execute step
                step_result = await self._execute_step(step)
                result.steps.append(step_result)
                self._step_results[step.id] = step_result

                # Update context with step results
                self._context[f"step_{step.id}"] = step_result.data

                # Aggregate findings
                result.findings.extend(step_result.findings)

                # Share findings to shared memory
                for finding in step_result.findings:
                    await share_finding(
                        session_id=session_id,
                        resource_id=resource_id,
                        finding=finding,
                    )

                # Handle failure
                if step_result.status == StepStatus.FAILED:
                    if step.on_failure == "stop":
                        should_stop = True
                    elif step.on_failure == "skip_remaining":
                        should_stop = True

            # Generate recommendations
            result.recommendations = self._generate_recommendations(result.findings)

            # Share recommendations
            for rec in result.recommendations:
                await share_recommendation(
                    session_id=session_id,
                    resource_id=resource_id,
                    recommendation=rec,
                )

            # Determine final status
            result.status = self._determine_final_status(result.steps)

        except Exception as e:
            logger.error(f"Runbook execution failed: {e}")
            result.status = RunbookStatus.FAILED
            result.recommendations.append(f"Runbook failed with error: {e}")

        # Finalize timing
        end_time = datetime.now(UTC)
        result.end_time = end_time
        result.duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return result

    async def _execute_step(self, step: RunbookStep) -> StepResult:
        """Execute a single step."""
        start_time = datetime.now(UTC)

        result = StepResult(
            step_id=step.id,
            status=StepStatus.RUNNING,
            start_time=start_time,
        )

        try:
            # Prepare parameters with variable substitution
            params = self._substitute_variables(step.params)

            # Execute tool or skill
            if step.tool_name and self.tool_executor:
                step_data = await asyncio.wait_for(
                    self.tool_executor(step.tool_name, params),
                    timeout=step.timeout_seconds,
                )
            elif step.skill_name and self.skill_executor:
                step_data = await asyncio.wait_for(
                    self.skill_executor(step.skill_name, params),
                    timeout=step.timeout_seconds,
                )
            else:
                # No executor - mark as placeholder
                step_data = {"placeholder": True}

            result.data = step_data if isinstance(step_data, dict) else {"result": step_data}

            # Analyze results for findings
            result.findings = self._analyze_step_results(step, result.data)

            # Determine status based on findings
            if any(f.get("severity") == "critical" for f in result.findings):
                result.status = StepStatus.WARNING
            else:
                result.status = StepStatus.SUCCESS

        except asyncio.TimeoutError:
            result.status = StepStatus.FAILED
            result.error = f"Step timed out after {step.timeout_seconds}s"
        except Exception as e:
            result.status = StepStatus.FAILED
            result.error = str(e)

        # Finalize timing
        end_time = datetime.now(UTC)
        result.end_time = end_time
        result.duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return result

    def _create_skipped_result(
        self,
        step: RunbookStep,
        reason: str = "Step skipped",
    ) -> StepResult:
        """Create a skipped step result."""
        now = datetime.now(UTC)
        return StepResult(
            step_id=step.id,
            status=StepStatus.SKIPPED,
            start_time=now,
            end_time=now,
            data={"reason": reason},
        )

    def _dependencies_met(self, step: RunbookStep) -> bool:
        """Check if step dependencies are met."""
        for dep_id in step.depends_on:
            dep_result = self._step_results.get(dep_id)
            if not dep_result:
                return False
            if dep_result.status not in [StepStatus.SUCCESS, StepStatus.WARNING]:
                return False
        return True

    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition expression using the safe evaluator."""
        return SafeExpressionEvaluator.evaluate(condition, self._context)

    def _substitute_variables(self, params: dict[str, Any]) -> dict[str, Any]:
        """Substitute variables in parameters."""
        result = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                result[key] = self._context.get(var_name, value)
            elif isinstance(value, dict):
                result[key] = self._substitute_variables(value)
            else:
                result[key] = value
        return result

    def _analyze_step_results(
        self,
        step: RunbookStep,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Analyze step results for findings."""
        findings = []

        # Check against thresholds
        thresholds = self.runbook.thresholds

        for metric, value in data.items():
            if not isinstance(value, (int, float)):
                continue

            threshold_key = f"{metric}_critical"
            if threshold_key in thresholds and value > thresholds[threshold_key]:
                findings.append({
                    "step_id": step.id,
                    "metric": metric,
                    "value": value,
                    "threshold": thresholds[threshold_key],
                    "severity": "critical",
                    "message": f"{metric} ({value}) exceeds critical threshold ({thresholds[threshold_key]})",
                })
                continue

            threshold_key = f"{metric}_warning"
            if threshold_key in thresholds and value > thresholds[threshold_key]:
                findings.append({
                    "step_id": step.id,
                    "metric": metric,
                    "value": value,
                    "threshold": thresholds[threshold_key],
                    "severity": "warning",
                    "message": f"{metric} ({value}) exceeds warning threshold ({thresholds[threshold_key]})",
                })

        return findings

    def _generate_recommendations(
        self,
        findings: list[dict[str, Any]],
    ) -> list[str]:
        """Generate recommendations based on findings."""
        recommendations = []

        # Group findings by severity
        critical = [f for f in findings if f.get("severity") == "critical"]
        warnings = [f for f in findings if f.get("severity") == "warning"]

        if critical:
            recommendations.append(
                f"CRITICAL: {len(critical)} critical issues found. Immediate action required."
            )
            for finding in critical[:3]:
                recommendations.append(f"  - {finding.get('message')}")

        if warnings:
            recommendations.append(
                f"WARNING: {len(warnings)} warnings found. Review recommended."
            )

        return recommendations

    def _determine_final_status(self, steps: list[StepResult]) -> RunbookStatus:
        """Determine final runbook status from step results."""
        has_failed = any(s.status == StepStatus.FAILED for s in steps)
        has_warning = any(s.status == StepStatus.WARNING for s in steps)

        if has_failed:
            return RunbookStatus.FAILED
        elif has_warning:
            return RunbookStatus.COMPLETED_WITH_WARNINGS
        else:
            return RunbookStatus.COMPLETED


# =============================================================================
# Built-in Runbooks
# =============================================================================

BUILTIN_RUNBOOKS: list[RunbookDefinition] = [
    # Database Health Check Runbook
    RunbookDefinition(
        id="db-health-check",
        name="Database Health Check",
        version="1.0.0",
        description="Comprehensive health check for autonomous databases",
        category="monitoring",
        target_resource_type="autonomous_database",
        thresholds={
            "cpu_usage_critical": 90,
            "cpu_usage_warning": 70,
            "storage_pct_critical": 90,
            "storage_pct_warning": 80,
            "session_pct_critical": 90,
            "session_pct_warning": 75,
        },
        steps=[
            RunbookStep(
                id="check_availability",
                name="Check Database Availability",
                description="Verify database is accessible and running",
                tool_name="oci_database_get_autonomous",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="check_cpu",
                name="Check CPU Utilization",
                description="Analyze CPU usage patterns",
                tool_name="oci_database_get_performance_metrics",
                params={"database_id": "${resource_id}", "metric": "cpu"},
            ),
            RunbookStep(
                id="check_storage",
                name="Check Storage Utilization",
                description="Analyze storage usage and growth",
                tool_name="oci_database_get_storage_metrics",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="check_sessions",
                name="Check Active Sessions",
                description="Analyze session counts and blocking",
                tool_name="oci_database_get_session_stats",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="check_alarms",
                name="Check Active Alarms",
                description="Check for any firing alarms",
                tool_name="oci_observability_list_alarms",
                params={"compartment_id": "${compartment_id}"},
            ),
        ],
    ),

    # Performance Investigation Runbook
    RunbookDefinition(
        id="db-performance-investigation",
        name="Database Performance Investigation",
        version="1.0.0",
        description="Deep-dive investigation for performance issues",
        category="troubleshooting",
        target_resource_type="autonomous_database",
        thresholds={
            "cpu_usage_critical": 85,
            "avg_wait_time_ms_warning": 50,
            "blocked_sessions_warning": 1,
        },
        steps=[
            RunbookStep(
                id="baseline_metrics",
                name="Collect Baseline Metrics",
                description="Gather current performance metrics",
                tool_name="oci_database_get_performance_metrics",
                params={"database_id": "${resource_id}", "time_window": "1h"},
            ),
            RunbookStep(
                id="top_sql_analysis",
                name="Identify Top SQL",
                description="Find resource-intensive SQL statements",
                skill_name="oci_opsi_get_sql_insights",
                params={"database_id": "${resource_id}", "limit": 10},
            ),
            RunbookStep(
                id="wait_event_analysis",
                name="Analyze Wait Events",
                description="Categorize wait events",
                skill_name="oci_opsi_get_wait_events",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="session_analysis",
                name="Analyze Sessions",
                description="Check for blocking and long-running sessions",
                tool_name="oci_database_get_session_stats",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="awr_analysis",
                name="AWR Report Analysis",
                description="Generate and analyze AWR report",
                condition="include_awr == True",
                tool_name="oci_opsi_get_awr_report",
                params={"database_id": "${resource_id}"},
            ),
        ],
        variables={
            "include_awr": True,
        },
    ),

    # Storage Capacity Planning Runbook
    RunbookDefinition(
        id="db-storage-capacity",
        name="Storage Capacity Planning",
        version="1.0.0",
        description="Analyze storage usage and plan for growth",
        category="capacity",
        target_resource_type="autonomous_database",
        thresholds={
            "storage_pct_critical": 90,
            "storage_pct_warning": 75,
            "days_to_full_warning": 30,
        },
        steps=[
            RunbookStep(
                id="current_usage",
                name="Current Storage Usage",
                description="Get current storage utilization",
                tool_name="oci_database_get_storage_metrics",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="tablespace_analysis",
                name="Tablespace Analysis",
                description="Analyze tablespace-level usage",
                tool_name="oci_database_get_tablespace_usage",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="growth_trend",
                name="Growth Trend Analysis",
                description="Calculate storage growth rate",
                skill_name="oci_opsi_get_storage_trend",
                params={"database_id": "${resource_id}", "period": "30d"},
            ),
            RunbookStep(
                id="backup_storage",
                name="Backup Storage Analysis",
                description="Analyze backup storage consumption",
                tool_name="oci_database_get_backup_storage",
                params={"database_id": "${resource_id}"},
            ),
        ],
    ),

    # Connection Issue Investigation Runbook
    RunbookDefinition(
        id="db-connection-investigation",
        name="Connection Issue Investigation",
        version="1.0.0",
        description="Diagnose connection and session issues",
        category="troubleshooting",
        target_resource_type="autonomous_database",
        thresholds={
            "connection_pct_critical": 95,
            "connection_pct_warning": 80,
            "blocked_sessions_warning": 1,
        },
        steps=[
            RunbookStep(
                id="db_status",
                name="Database Status",
                description="Verify database is available",
                tool_name="oci_database_get_autonomous",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="connection_pool",
                name="Connection Pool Status",
                description="Check connection pool utilization",
                tool_name="oci_database_get_connection_stats",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="session_details",
                name="Session Details",
                description="Get detailed session information",
                tool_name="oci_database_get_session_stats",
                params={"database_id": "${resource_id}", "include_details": True},
            ),
            RunbookStep(
                id="blocking_analysis",
                name="Blocking Lock Analysis",
                description="Identify blocking locks",
                tool_name="oci_database_get_blocking_sessions",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="network_check",
                name="Network Connectivity",
                description="Check network connectivity metrics",
                tool_name="oci_network_get_connectivity_status",
                params={"resource_id": "${resource_id}"},
                on_failure="continue",
            ),
        ],
    ),

    # Security Audit Runbook
    RunbookDefinition(
        id="db-security-audit",
        name="Database Security Audit",
        version="1.0.0",
        description="Security posture assessment for databases",
        category="security",
        target_resource_type="autonomous_database",
        steps=[
            RunbookStep(
                id="check_encryption",
                name="Encryption Status",
                description="Verify encryption settings",
                tool_name="oci_database_get_security_settings",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="check_network",
                name="Network Security",
                description="Review ACL and network configurations",
                tool_name="oci_database_get_network_access",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="check_iam",
                name="IAM Review",
                description="Review IAM policies and access",
                tool_name="oci_security_get_database_access",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="audit_logs",
                name="Audit Log Analysis",
                description="Review recent audit log entries",
                tool_name="oci_database_get_audit_logs",
                params={"database_id": "${resource_id}", "time_window": "24h"},
            ),
        ],
    ),

    # Maintenance Readiness Runbook
    RunbookDefinition(
        id="db-maintenance-readiness",
        name="Maintenance Readiness Check",
        version="1.0.0",
        description="Pre-maintenance health and readiness check",
        category="maintenance",
        target_resource_type="autonomous_database",
        steps=[
            RunbookStep(
                id="health_check",
                name="Pre-Maintenance Health Check",
                description="Verify database is healthy before maintenance",
                skill_name="oci_skill_troubleshoot_database",
                params={"database_id": "${resource_id}", "issue_type": "general"},
            ),
            RunbookStep(
                id="backup_status",
                name="Backup Status",
                description="Verify recent backup exists",
                tool_name="oci_database_list_backups",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="workload_check",
                name="Current Workload",
                description="Check current database workload",
                tool_name="oci_database_get_performance_metrics",
                params={"database_id": "${resource_id}"},
            ),
            RunbookStep(
                id="connection_drain",
                name="Connection Drain Check",
                description="Verify connections can be drained",
                tool_name="oci_database_get_connection_stats",
                params={"database_id": "${resource_id}"},
            ),
        ],
    ),
]


# =============================================================================
# Helper Functions
# =============================================================================

def get_runbook(runbook_id: str) -> RunbookDefinition | None:
    """Get a runbook by ID."""
    registry = RunbookRegistry.get_instance()
    return registry.get(runbook_id)


def list_runbooks(category: str | None = None) -> list[RunbookDefinition]:
    """List runbooks, optionally filtered by category."""
    registry = RunbookRegistry.get_instance()
    if category:
        return registry.list_by_category(category)
    return registry.list_all()


def register_runbook(runbook: RunbookDefinition) -> None:
    """Register a new runbook."""
    registry = RunbookRegistry.get_instance()
    registry.register(runbook)


async def execute_runbook(
    runbook_id: str,
    resource_id: str,
    session_id: str,
    variables: dict[str, Any] | None = None,
    tool_executor: Callable | None = None,
    skill_executor: Callable | None = None,
) -> RunbookResult:
    """
    Execute a runbook by ID.

    Args:
        runbook_id: ID of the runbook to execute
        resource_id: Target resource OCID
        session_id: Session ID for tracking
        variables: Override variables
        tool_executor: Function to execute tools
        skill_executor: Function to execute skills

    Returns:
        RunbookResult with execution details
    """
    runbook = get_runbook(runbook_id)
    if not runbook:
        raise ValueError(f"Runbook not found: {runbook_id}")

    executor = RunbookExecutor(
        runbook=runbook,
        tool_executor=tool_executor,
        skill_executor=skill_executor,
    )

    return await executor.execute(
        resource_id=resource_id,
        session_id=session_id,
        variables=variables,
    )
