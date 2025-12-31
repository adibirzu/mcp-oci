"""
Skills package - High-level workflow skills for OCI operations.

Skills are composite operations that orchestrate multiple tools to accomplish
complex tasks. They encode operational best practices and return synthesized,
actionable output.

Key components:
- executor: SkillExecutor for coordinating tool calls with progress tracking
- agent: Agent context, conversation memory, and LLM sampling utilities
- troubleshoot: Instance troubleshooting skill
- discovery: Tool and skill registration and discovery utilities
- tools: MCP tool registration for skills
"""

from .agent import (
    AgentContext,
    AnalysisRequest,
    AnalysisType,
    ConversationMemory,
    Message,
    MessageRole,
    SamplingClient,
    create_analysis_request,
    create_diagnostic_request,
    create_recommendation_request,
)
from .discovery import (
    DetailLevel,
    ListDomainsInput,
    ResourceType,
    SearchToolsInput,
    SkillInfo,
    ToolInfo,
    ToolRegistry,
    auto_register_tool,
    register_skill_from_metadata,
    tool_registry,
)
from .executor import (
    SkillExecutor,
    ToolCallResult,
    get_skill_registry,
    list_skills,
    register_skill,
)
from .tools import register_skill_tools

__all__ = [
    # Executor
    "SkillExecutor",
    "ToolCallResult",
    "register_skill",
    "get_skill_registry",
    "list_skills",
    # Discovery
    "DetailLevel",
    "ResourceType",
    "SearchToolsInput",
    "ListDomainsInput",
    "ToolInfo",
    "SkillInfo",
    "ToolRegistry",
    "tool_registry",
    "auto_register_tool",
    "register_skill_from_metadata",
    # Agent utilities
    "MessageRole",
    "Message",
    "ConversationMemory",
    "AgentContext",
    "AnalysisType",
    "AnalysisRequest",
    "SamplingClient",
    "create_analysis_request",
    "create_diagnostic_request",
    "create_recommendation_request",
    # Tool registration
    "register_skill_tools",
]
