"""
Agent utilities for LLM/Agent communication in skills.

Provides:
- AgentContext: Carry context between tool calls and LLM reasoning
- SamplingClient: Make LLM calls via MCP sampling protocol
- ConversationMemory: Track conversation history for multi-turn interactions
- AnalysisRequest: Structure requests for LLM analysis
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastmcp import Context
from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str, Enum):
    """Role of a message in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    """A single message in a conversation."""
    role: MessageRole
    content: str
    name: str | None = None  # Tool name if role is TOOL
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationMemory(BaseModel):
    """Tracks conversation history for multi-turn interactions."""

    messages: list[Message] = Field(default_factory=list)
    max_messages: int = Field(default=50, description="Max messages to retain")
    max_tokens_estimate: int = Field(default=8000, description="Approx token budget")

    def add_message(
        self,
        role: MessageRole,
        content: str,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to the conversation."""
        msg = Message(
            role=role,
            content=content,
            name=name,
            metadata=metadata or {},
        )
        self.messages.append(msg)
        self._trim_if_needed()

    def add_user_message(self, content: str) -> None:
        self.add_message(MessageRole.USER, content)

    def add_assistant_message(self, content: str) -> None:
        self.add_message(MessageRole.ASSISTANT, content)

    def add_tool_result(self, tool_name: str, result: str) -> None:
        self.add_message(MessageRole.TOOL, result, name=tool_name)

    def add_system_message(self, content: str) -> None:
        self.add_message(MessageRole.SYSTEM, content)

    def get_messages_for_llm(self) -> list[dict[str, Any]]:
        """Format messages for LLM API call."""
        return [
            {
                "role": msg.role.value,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {}),
            }
            for msg in self.messages
        ]

    def get_context_summary(self, max_chars: int = 2000) -> str:
        """Get a summary of recent conversation for context."""
        recent = self.messages[-10:]  # Last 10 messages
        lines = []
        for msg in recent:
            prefix = f"[{msg.role.value}]"
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            lines.append(f"{prefix}: {content}")

        summary = "\n".join(lines)
        if len(summary) > max_chars:
            summary = summary[-max_chars:]
        return summary

    def _trim_if_needed(self) -> None:
        """Remove old messages if over limits."""
        while len(self.messages) > self.max_messages:
            # Keep system messages, remove oldest non-system
            for i, msg in enumerate(self.messages):
                if msg.role != MessageRole.SYSTEM:
                    self.messages.pop(i)
                    break

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()


class AgentContext(BaseModel):
    """
    Context carried between tool calls and LLM reasoning steps.

    This enables skills to:
    - Pass structured data between execution steps
    - Maintain conversation history
    - Track goals and progress
    - Store intermediate results
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Identification
    session_id: str = Field(default="", description="Unique session identifier")
    skill_name: str = Field(default="", description="Currently executing skill")

    # OCI Context (inherited from skill params)
    profile: str | None = None
    region: str | None = None
    compartment_id: str | None = None
    tenancy_id: str | None = None

    # Task Context
    goal: str = Field(default="", description="High-level goal being accomplished")
    sub_goals: list[str] = Field(default_factory=list, description="Breakdown of goal into steps")
    current_step: int = Field(default=0, description="Current step index")

    # Data Storage
    findings: dict[str, Any] = Field(default_factory=dict, description="Discovered information")
    intermediate_results: dict[str, Any] = Field(default_factory=dict, description="Step results")
    recommendations: list[str] = Field(
        default_factory=list, description="Generated recommendations"
    )

    # Conversation
    memory: ConversationMemory = Field(default_factory=ConversationMemory)

    # Metadata
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_finding(self, key: str, value: Any) -> None:
        """Add a finding to the context."""
        self.findings[key] = value

    def add_result(self, step_name: str, result: Any) -> None:
        """Store an intermediate result."""
        self.intermediate_results[step_name] = result

    def add_recommendation(self, rec: str) -> None:
        """Add a recommendation."""
        if rec not in self.recommendations:
            self.recommendations.append(rec)

    def get_elapsed_seconds(self) -> float:
        """Get elapsed time since start."""
        return (datetime.now(UTC) - self.start_time).total_seconds()

    def to_prompt_context(self) -> str:
        """Format context for inclusion in LLM prompts."""
        parts = []

        if self.goal:
            parts.append(f"Goal: {self.goal}")

        if self.findings:
            parts.append("Findings:")
            for key, value in self.findings.items():
                if isinstance(value, dict):
                    parts.append(f"  {key}: {json.dumps(value, indent=2)}")
                else:
                    parts.append(f"  {key}: {value}")

        if self.recommendations:
            parts.append("Current recommendations:")
            for rec in self.recommendations:
                parts.append(f"  - {rec}")

        return "\n".join(parts)

    @classmethod
    def from_skill_params(cls, params: Any, skill_name: str = "") -> AgentContext:
        """Create AgentContext from skill input parameters."""
        ctx = cls(skill_name=skill_name)

        # Extract OCI context if available
        if hasattr(params, "profile"):
            ctx.profile = params.profile
        if hasattr(params, "region"):
            ctx.region = params.region
        if hasattr(params, "compartment_id"):
            ctx.compartment_id = params.compartment_id

        return ctx


class AnalysisType(str, Enum):
    """Types of LLM analysis requests."""
    SUMMARIZE = "summarize"
    DIAGNOSE = "diagnose"
    RECOMMEND = "recommend"
    EXPLAIN = "explain"
    CLASSIFY = "classify"
    COMPARE = "compare"


class AnalysisRequest(BaseModel):
    """Structured request for LLM analysis."""

    analysis_type: AnalysisType
    data: dict[str, Any] = Field(default_factory=dict)
    question: str = Field(default="", description="Specific question to answer")
    context: str = Field(default="", description="Additional context")
    constraints: list[str] = Field(default_factory=list, description="Constraints/requirements")
    output_format: str = Field(default="text", description="Expected output format")

    def to_prompt(self) -> str:
        """Convert request to LLM prompt."""
        parts = []

        # Analysis type instruction
        type_instructions = {
            AnalysisType.SUMMARIZE: "Summarize the following data concisely:",
            AnalysisType.DIAGNOSE: (
                "Analyze the following data and identify any issues or problems:"
            ),
            AnalysisType.RECOMMEND: (
                "Based on the following data, provide actionable recommendations:"
            ),
            AnalysisType.EXPLAIN: "Explain the following in clear, understandable terms:",
            AnalysisType.CLASSIFY: "Classify the following data into appropriate categories:",
            AnalysisType.COMPARE: "Compare the following items and highlight key differences:",
        }
        parts.append(type_instructions.get(self.analysis_type, "Analyze the following:"))

        # Add data
        if self.data:
            parts.append("\nData:")
            parts.append(json.dumps(self.data, indent=2, default=str))

        # Add context
        if self.context:
            parts.append(f"\nContext: {self.context}")

        # Add specific question
        if self.question:
            parts.append(f"\nQuestion: {self.question}")

        # Add constraints
        if self.constraints:
            parts.append("\nConstraints:")
            for c in self.constraints:
                parts.append(f"  - {c}")

        # Output format instruction
        if self.output_format == "json":
            parts.append("\nRespond with valid JSON only.")
        elif self.output_format == "bullets":
            parts.append("\nRespond with a bulleted list.")
        elif self.output_format == "markdown":
            parts.append("\nRespond with markdown formatting.")

        return "\n".join(parts)


class SamplingClient:
    """
    Client for making LLM calls via MCP sampling protocol.

    This allows skills to request LLM reasoning/analysis during execution.
    The MCP server acts as a proxy to the LLM.
    """

    def __init__(self, ctx: Context | None = None):
        self.ctx = ctx
        self._call_count = 0
        self._total_time_ms = 0.0

    async def analyze(
        self,
        request: AnalysisRequest,
        agent_context: AgentContext | None = None,
    ) -> str:
        """
        Request LLM analysis.

        Args:
            request: The analysis request
            agent_context: Optional context for conversation continuity

        Returns:
            LLM response text
        """
        prompt = request.to_prompt()

        # Add agent context if available
        if agent_context:
            context_str = agent_context.to_prompt_context()
            if context_str:
                prompt = f"Background:\n{context_str}\n\n{prompt}"

        return await self.sample(prompt, agent_context)

    async def sample(
        self,
        prompt: str,
        agent_context: AgentContext | None = None,
        system_prompt: str | None = None,
        max_tokens: int = 1000,
    ) -> str:
        """
        Make a sampling request to the LLM.

        This uses the MCP sampling protocol if available, otherwise
        returns a placeholder indicating sampling is not available.

        Args:
            prompt: The user prompt
            agent_context: Optional context for conversation history
            system_prompt: Optional system prompt override
            max_tokens: Maximum tokens in response

        Returns:
            LLM response text
        """
        start_time = time.time()
        self._call_count += 1

        # Build messages
        messages = []

        # Add system prompt
        if system_prompt:
            messages.append({"role": "user", "content": system_prompt})

        # Add conversation history if available
        if agent_context and agent_context.memory.messages:
            messages.extend(agent_context.memory.get_messages_for_llm())

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        # Try MCP sampling if context available
        if self.ctx is not None:
            try:
                # Check if sampling is available
                if hasattr(self.ctx, "sample") or hasattr(self.ctx, "create_message"):
                    # Use MCP sampling protocol
                    # Note: This depends on the MCP client supporting sampling
                    result = await self._mcp_sample(messages, max_tokens)

                    # Update conversation memory
                    if agent_context:
                        agent_context.memory.add_user_message(prompt)
                        agent_context.memory.add_assistant_message(result)

                    self._total_time_ms += (time.time() - start_time) * 1000
                    return result
            except Exception:
                # Fall through to placeholder if sampling fails
                pass

        # Sampling not available - return informative placeholder
        self._total_time_ms += (time.time() - start_time) * 1000

        return self._generate_placeholder_response(prompt, messages)

    async def _mcp_sample(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
    ) -> str:
        """
        Make actual MCP sampling call.

        This uses the MCP sampling protocol to request LLM completion.
        """
        if self.ctx is None:
            raise RuntimeError("No MCP context available for sampling")

        # MCP sampling request format
        # Note: The exact API depends on the MCP SDK version
        try:
            # Try newer API first
            if hasattr(self.ctx, "sample"):
                response = await self.ctx.sample(
                    messages=messages,
                    max_tokens=max_tokens,
                )
                return response.content if hasattr(response, "content") else str(response)

            # Try create_message API
            if hasattr(self.ctx, "create_message"):
                response = await self.ctx.create_message(
                    messages=messages,
                    max_tokens=max_tokens,
                )
                return response.content[0].text if response.content else ""

        except AttributeError:
            pass

        raise RuntimeError("MCP sampling not supported by current context")

    def _generate_placeholder_response(
        self,
        prompt: str,
        messages: list[dict[str, Any]],
    ) -> str:
        """Generate a placeholder response when sampling is unavailable."""
        # Extract key information from prompt
        if "diagnose" in prompt.lower():
            return (
                "[LLM Analysis Unavailable]\n"
                "Diagnosis would analyze the provided data for issues.\n"
                "Please review the raw data manually or use an external LLM."
            )
        elif "recommend" in prompt.lower():
            return (
                "[LLM Analysis Unavailable]\n"
                "Recommendations would be generated based on findings.\n"
                "Manual review of findings is recommended."
            )
        elif "summarize" in prompt.lower():
            return (
                "[LLM Analysis Unavailable]\n"
                "A summary would condense the key points.\n"
                "Please review the detailed data directly."
            )
        else:
            return (
                "[LLM Analysis Unavailable]\n"
                "This skill requested LLM analysis but sampling is not available.\n"
                "The skill will continue with rule-based analysis."
            )

    def get_stats(self) -> dict[str, Any]:
        """Get sampling statistics."""
        return {
            "call_count": self._call_count,
            "total_time_ms": self._total_time_ms,
            "avg_time_ms": self._total_time_ms / self._call_count if self._call_count > 0 else 0,
        }


# Convenience functions
def create_analysis_request(
    analysis_type: str | AnalysisType,
    data: dict[str, Any],
    question: str = "",
    **kwargs: Any,
) -> AnalysisRequest:
    """Create an analysis request with common defaults."""
    if isinstance(analysis_type, str):
        analysis_type = AnalysisType(analysis_type)

    return AnalysisRequest(
        analysis_type=analysis_type,
        data=data,
        question=question,
        **kwargs,
    )


def create_diagnostic_request(
    data: dict[str, Any],
    question: str = "What issues or problems are present?",
) -> AnalysisRequest:
    """Create a diagnostic analysis request."""
    return create_analysis_request(
        AnalysisType.DIAGNOSE,
        data,
        question,
        output_format="markdown",
    )


def create_recommendation_request(
    findings: dict[str, Any],
    constraints: list[str] | None = None,
) -> AnalysisRequest:
    """Create a recommendation request."""
    return create_analysis_request(
        AnalysisType.RECOMMEND,
        findings,
        "What actions should be taken?",
        constraints=constraints or [],
        output_format="bullets",
    )
