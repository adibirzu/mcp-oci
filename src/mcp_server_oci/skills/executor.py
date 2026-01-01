"""
Skill Executor - Framework for coordinating tool calls within skills.

The SkillExecutor provides:
- Consistent tool call wrapping with timing and error handling
- Progress reporting through MCP Context
- Result aggregation and formatting
- OCI context propagation to child tools
- LLM analysis integration via SamplingClient
- Agent context management for multi-step workflows
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, TypeVar

from fastmcp import Context
from pydantic import BaseModel

from mcp_server_oci.core import (
    BaseSkillInput,
    SkillMetadata,
    SkillProgress,
    SkillResult,
    SkillStep,
    get_logger,
)

if TYPE_CHECKING:
    from .agent import AgentContext, SamplingClient

logger = get_logger("oci-mcp.skills.executor")

T = TypeVar("T", bound=BaseModel)


class ToolCallResult:
    """Result of a tool call with metadata."""

    def __init__(
        self,
        tool_name: str,
        success: bool,
        data: Any = None,
        error: str | None = None,
        duration_ms: float = 0,
    ):
        self.tool_name = tool_name
        self.success = success
        self.data = data
        self.error = error
        self.duration_ms = duration_ms

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class SkillExecutor:
    """
    Executes skills by coordinating tool calls with progress tracking.

    Enhanced with:
    - LLM analysis integration via SamplingClient
    - Agent context management for multi-step workflows
    - Skill chaining support

    Usage:
        async def my_skill(params: MySkillInput, ctx: Context) -> str:
            executor = SkillExecutor(
                skill_name="my_skill",
                ctx=ctx,
                params=params,
            )

            # Define steps
            executor.add_step("check_status", "Check resource status", tool_name="get_status")
            executor.add_step("analyze", "Analyze metrics", tool_name="get_metrics")
            executor.add_step("llm_diagnose", "LLM diagnosis", is_llm_step=True)
            executor.add_step("recommend", "Generate recommendations")

            # Execute steps
            status = await executor.call_tool("check_status", get_status, status_params)
            metrics = await executor.call_tool("analyze", get_metrics, metrics_params)

            # LLM analysis step
            diagnosis = await executor.run_llm_analysis(
                "llm_diagnose",
                analysis_type="diagnose",
                data={"status": status, "metrics": metrics},
            )

            # Build and return result
            result = executor.build_result(
                success=True,
                summary="Analysis complete",
                details={"status": status, "metrics": metrics, "diagnosis": diagnosis},
                recommendations=["Consider scaling up"]
            )
            if params.response_format == ResponseFormat.MARKDOWN:
                return result.to_markdown()
            return result.model_dump_json()
    """

    def __init__(
        self,
        skill_name: str,
        ctx: Context | None = None,
        params: BaseSkillInput | None = None,
        agent_context: AgentContext | None = None,
    ):
        self.skill_name = skill_name
        self.ctx = ctx
        self.params = params
        self.start_time = time.time()

        # Progress tracking
        self.progress = SkillProgress(
            skill_name=skill_name,
            total_steps=0,
            steps=[],
        )

        # Tool call results
        self.tool_results: dict[str, ToolCallResult] = {}

        # OCI context for propagation
        self._oci_context: dict[str, Any] = {}
        if params:
            self._oci_context = {
                "profile": params.profile,
                "region": params.region,
                "compartment_id": params.compartment_id,
            }

        # Agent context for LLM interactions
        self._agent_context = agent_context
        if agent_context is None and params:
            # Lazily create agent context when needed
            self._agent_context = None

        # Sampling client for LLM calls
        self._sampling_client: SamplingClient | None = None

        # Child skill executors for chaining
        self._child_executors: list[SkillExecutor] = []

    def add_step(
        self,
        name: str,
        description: str,
        tool_name: str | None = None,
        is_llm_step: bool = False,
    ) -> None:
        """
        Add a step to the skill workflow.

        Args:
            name: Step identifier for referencing in call_tool
            description: Human-readable description shown in progress
            tool_name: MCP tool name if this step calls a tool
            is_llm_step: Whether this step involves LLM reasoning
        """
        step = SkillStep(
            name=name,
            description=description,
            tool_name=tool_name if not is_llm_step else "llm_analysis",
            status="pending",
        )
        self.progress.steps.append(step)
        self.progress.total_steps = len(self.progress.steps)

    async def call_tool(
        self,
        step_name: str,
        tool_func: Callable[..., Coroutine[Any, Any, Any]],
        params: BaseModel | None = None,
        **kwargs: Any,
    ) -> ToolCallResult:
        """
        Call a tool function with progress tracking.

        Args:
            step_name: The step name (must have been added with add_step)
            tool_func: The async tool function to call
            params: Pydantic model for tool parameters
            **kwargs: Additional kwargs passed to tool function

        Returns:
            ToolCallResult with success status, data, and timing
        """
        # Mark step as running
        self.progress.advance(step_name)
        await self._report_progress()

        start = time.time()
        try:
            # Propagate OCI context if params is a model with these fields
            if params and hasattr(params, "model_copy"):
                # Inject OCI context into params if fields exist and are None
                update_data = {}
                for field in ["profile", "region", "compartment_id"]:
                    if hasattr(params, field) and getattr(params, field) is None:
                        context_val = self._oci_context.get(field)
                        if context_val:
                            update_data[field] = context_val
                if update_data:
                    params = params.model_copy(update=update_data)

            # Call the tool
            if params is not None:
                if self.ctx is not None:
                    result = await tool_func(params, self.ctx)
                else:
                    result = await tool_func(params)
            else:
                if self.ctx is not None:
                    result = await tool_func(**kwargs, ctx=self.ctx)
                else:
                    result = await tool_func(**kwargs)

            duration_ms = (time.time() - start) * 1000

            # Parse result if JSON string
            parsed_data = result
            if isinstance(result, str):
                try:
                    parsed_data = json.loads(result)
                except json.JSONDecodeError:
                    parsed_data = result

            tool_result = ToolCallResult(
                tool_name=step_name,
                success=True,
                data=parsed_data,
                duration_ms=duration_ms,
            )

            self.progress.complete_step(step_name, result=parsed_data, duration_ms=duration_ms)
            self.tool_results[step_name] = tool_result

            logger.debug(f"Tool {step_name} completed in {duration_ms:.0f}ms")

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            error_msg = str(e)

            tool_result = ToolCallResult(
                tool_name=step_name,
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

            self.progress.fail_step(step_name, error=error_msg)
            self.tool_results[step_name] = tool_result

            logger.warning(f"Tool {step_name} failed: {error_msg}")

        await self._report_progress()
        return tool_result

    async def run_custom_step(
        self,
        step_name: str,
        func: Callable[[], Coroutine[Any, Any, Any]],
    ) -> ToolCallResult:
        """
        Run a custom async function as a step (not a tool call).

        Useful for data processing, analysis, or decision logic.
        """
        self.progress.advance(step_name)
        await self._report_progress()

        start = time.time()
        try:
            result = await func()
            duration_ms = (time.time() - start) * 1000

            tool_result = ToolCallResult(
                tool_name=step_name,
                success=True,
                data=result,
                duration_ms=duration_ms,
            )

            self.progress.complete_step(step_name, result=result, duration_ms=duration_ms)
            self.tool_results[step_name] = tool_result

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            error_msg = str(e)

            tool_result = ToolCallResult(
                tool_name=step_name,
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

            self.progress.fail_step(step_name, error=error_msg)
            self.tool_results[step_name] = tool_result

        await self._report_progress()
        return tool_result

    def skip_step(self, step_name: str, reason: str = "Skipped") -> None:
        """Mark a step as skipped (e.g., due to conditional logic)."""
        for step in self.progress.steps:
            if step.name == step_name:
                step.status = "skipped"
                step.error = reason
                break

    def get_result(self, step_name: str) -> Any | None:
        """Get the result data from a completed step."""
        result = self.tool_results.get(step_name)
        return result.data if result and result.success else None

    def build_result(
        self,
        success: bool,
        summary: str,
        details: dict[str, Any] | None = None,
        recommendations: list[str] | None = None,
    ) -> SkillResult:
        """
        Build the final skill result with all metadata.

        Args:
            success: Overall success status
            summary: Brief summary of what was done/found
            details: Structured details dictionary
            recommendations: List of actionable recommendations

        Returns:
            SkillResult ready for formatting
        """
        execution_time_ms = (time.time() - self.start_time) * 1000

        # Collect raw data if requested
        raw_data = None
        if self.params and self.params.include_raw_data:
            raw_data = {
                name: result.as_dict()
                for name, result in self.tool_results.items()
            }

        # Include progress if verbose
        progress = None
        if self.params and self.params.verbose:
            progress = self.progress

        return SkillResult(
            skill_name=self.skill_name,
            success=success,
            summary=summary,
            details=details or {},
            recommendations=recommendations or [],
            raw_data=raw_data,
            progress=progress,
            execution_time_ms=execution_time_ms,
        )

    # =========================================================================
    # LLM Analysis Methods
    # =========================================================================

    def get_agent_context(self) -> AgentContext:
        """Get or create the agent context for this executor."""
        if self._agent_context is None:
            from .agent import AgentContext
            self._agent_context = AgentContext.from_skill_params(
                self.params, skill_name=self.skill_name
            )
        return self._agent_context

    def get_sampling_client(self) -> SamplingClient:
        """Get or create the sampling client for LLM calls."""
        if self._sampling_client is None:
            from .agent import SamplingClient
            self._sampling_client = SamplingClient(ctx=self.ctx)
        return self._sampling_client

    async def run_llm_analysis(
        self,
        step_name: str,
        analysis_type: str,
        data: dict[str, Any],
        question: str = "",
        constraints: list[str] | None = None,
        output_format: str = "text",
    ) -> ToolCallResult:
        """
        Run an LLM analysis step.

        Args:
            step_name: The step name (must have been added with add_step)
            analysis_type: Type of analysis (summarize, diagnose, recommend,
                explain, classify, compare)
            data: Data to analyze
            question: Specific question to answer
            constraints: List of constraints for the analysis
            output_format: Expected output format (text, json, bullets, markdown)

        Returns:
            ToolCallResult with the LLM response
        """
        from .agent import AnalysisRequest, AnalysisType

        self.progress.advance(step_name)
        await self._report_progress()

        start = time.time()
        try:
            # Build analysis request
            request = AnalysisRequest(
                analysis_type=AnalysisType(analysis_type),
                data=data,
                question=question,
                constraints=constraints or [],
                output_format=output_format,
            )

            # Get agent context with findings
            agent_ctx = self.get_agent_context()

            # Add current findings to context
            for name, result in self.tool_results.items():
                if result.success and result.data:
                    agent_ctx.add_finding(name, result.data)

            # Make LLM call
            sampling = self.get_sampling_client()
            response = await sampling.analyze(request, agent_ctx)

            duration_ms = (time.time() - start) * 1000

            tool_result = ToolCallResult(
                tool_name=step_name,
                success=True,
                data=response,
                duration_ms=duration_ms,
            )

            self.progress.complete_step(step_name, result=response, duration_ms=duration_ms)
            self.tool_results[step_name] = tool_result

            logger.debug(f"LLM analysis {step_name} completed in {duration_ms:.0f}ms")

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            error_msg = str(e)

            tool_result = ToolCallResult(
                tool_name=step_name,
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

            self.progress.fail_step(step_name, error=error_msg)
            self.tool_results[step_name] = tool_result

            logger.warning(f"LLM analysis {step_name} failed: {error_msg}")

        await self._report_progress()
        return tool_result

    async def generate_recommendations(
        self,
        step_name: str = "generate_recommendations",
        constraints: list[str] | None = None,
    ) -> list[str]:
        """
        Generate recommendations based on all collected findings.

        This is a convenience method that collects all findings and
        asks the LLM to generate actionable recommendations.

        Returns:
            List of recommendation strings
        """
        # Collect all findings
        findings = {}
        for name, result in self.tool_results.items():
            if result.success and result.data:
                findings[name] = result.data

        if not findings:
            return ["No data available for recommendations."]

        # Run LLM analysis
        result = await self.run_llm_analysis(
            step_name=step_name,
            analysis_type="recommend",
            data=findings,
            question="Based on these findings, what specific actions should be taken?",
            constraints=constraints or [
                "Be specific and actionable",
                "Prioritize by impact",
                "Consider cost implications",
            ],
            output_format="bullets",
        )

        if result.success and result.data:
            # Parse bullet points from response
            lines = result.data.strip().split("\n")
            recommendations = [
                line.lstrip("- •*").strip()
                for line in lines
                if line.strip() and not line.startswith("[")
            ]
            return recommendations if recommendations else [result.data]

        return ["Unable to generate recommendations."]

    # =========================================================================
    # Skill Chaining Methods
    # =========================================================================

    async def call_skill(
        self,
        step_name: str,
        skill_func: Callable[..., Coroutine[Any, Any, str]],
        params: BaseModel,
    ) -> ToolCallResult:
        """
        Call another skill as a sub-step.

        This enables skill chaining - one skill can invoke other skills
        to accomplish complex multi-stage workflows.

        Args:
            step_name: The step name for this sub-skill call
            skill_func: The skill function to call
            params: Parameters for the skill

        Returns:
            ToolCallResult with the skill's output
        """
        self.progress.advance(step_name)
        await self._report_progress()

        start = time.time()
        try:
            # Call the skill
            result = await skill_func(params, self.ctx)

            duration_ms = (time.time() - start) * 1000

            # Parse result if JSON
            parsed_data = result
            if isinstance(result, str):
                try:
                    parsed_data = json.loads(result)
                except json.JSONDecodeError:
                    parsed_data = result

            tool_result = ToolCallResult(
                tool_name=step_name,
                success=True,
                data=parsed_data,
                duration_ms=duration_ms,
            )

            self.progress.complete_step(step_name, result=parsed_data, duration_ms=duration_ms)
            self.tool_results[step_name] = tool_result

            logger.debug(f"Sub-skill {step_name} completed in {duration_ms:.0f}ms")

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            error_msg = str(e)

            tool_result = ToolCallResult(
                tool_name=step_name,
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

            self.progress.fail_step(step_name, error=error_msg)
            self.tool_results[step_name] = tool_result

            logger.warning(f"Sub-skill {step_name} failed: {error_msg}")

        await self._report_progress()
        return tool_result

    def create_child_executor(
        self,
        skill_name: str,
        params: BaseSkillInput | None = None,
    ) -> SkillExecutor:
        """
        Create a child executor for nested skill execution.

        Child executors share the same context and agent context,
        enabling state sharing between parent and child skills.
        """
        child = SkillExecutor(
            skill_name=skill_name,
            ctx=self.ctx,
            params=params or self.params,
            agent_context=self.get_agent_context(),
        )
        self._child_executors.append(child)
        return child

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _report_progress(self) -> None:
        """Report progress to MCP context if available."""
        if self.ctx is not None:
            # FastMCP report_progress takes (progress, total)
            # Use contextlib.suppress for cleaner exception handling
            from contextlib import suppress
            with suppress(Exception):
                await self.ctx.report_progress(
                    self.progress.percent_complete / 100
                )


# Skill registry for discovery
_skill_registry: dict[str, SkillMetadata] = {}


def register_skill(metadata: SkillMetadata) -> None:
    """Register a skill in the global registry."""
    _skill_registry[metadata.name] = metadata


def get_skill_registry() -> dict[str, SkillMetadata]:
    """Get all registered skills."""
    return _skill_registry.copy()


def list_skills(domain: str | None = None) -> list[SkillMetadata]:
    """List all registered skills, optionally filtered by domain."""
    skills = list(_skill_registry.values())
    if domain:
        skills = [s for s in skills if s.domain == domain]
    return skills
