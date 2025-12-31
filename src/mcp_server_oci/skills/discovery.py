"""
Tool and Skill discovery implementation for progressive disclosure pattern.

Enables agents to explore available tools and skills efficiently without loading
all definitions upfront. Supports searching, filtering, and retrieving metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from mcp_server_oci.core import SkillMetadata


class DetailLevel(str, Enum):
    """Level of detail for tool discovery."""
    NAME_ONLY = "name_only"           # Just tool names
    SUMMARY = "summary"               # Names + one-line descriptions
    FULL = "full"                     # Complete schema and documentation


class ResourceType(str, Enum):
    """Type of discoverable resource."""
    TOOL = "tool"                     # Atomic MCP tool
    SKILL = "skill"                   # Composite skill (orchestrates multiple tools)


class SearchToolsInput(BaseModel):
    """Input for tool search."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    query: str = Field(
        ...,
        description="Search query (e.g., 'cost', 'compute instances', 'database')"
    )
    detail_level: DetailLevel = Field(
        default=DetailLevel.SUMMARY,
        description="Level of detail: 'name_only', 'summary', or 'full'"
    )
    domain: str | None = Field(
        default=None,
        description="Filter by domain: cost, compute, database, network, security, observability"
    )
    resource_type: ResourceType | None = Field(
        default=None,
        description="Filter by resource type: 'tool' or 'skill'. If not specified, returns both."
    )
    limit: int = Field(
        default=20,
        description="Maximum results to return",
        ge=1,
        le=50
    )


class ListDomainsInput(BaseModel):
    """Input for listing available domains."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    include_tool_count: bool = Field(
        default=True,
        description="Include number of tools per domain"
    )


@dataclass
class ToolInfo:
    """Tool information for discovery."""
    name: str
    domain: str
    summary: str
    full_description: str
    input_schema: dict[str, Any]
    annotations: dict[str, Any]
    tier: int = 2  # 1-4 (performance tier)
    examples: list[dict[str, Any]] = field(default_factory=list)
    resource_type: ResourceType = ResourceType.TOOL


@dataclass
class SkillInfo:
    """Skill information for discovery (composite operations)."""
    name: str
    display_name: str
    domain: str
    summary: str
    full_description: str
    input_schema: dict[str, Any]
    tools_used: list[str]  # List of tool names this skill orchestrates
    tier: int = 3  # Skills are typically tier 3
    estimated_duration: str = "1-30s"
    resource_type: ResourceType = ResourceType.SKILL

    @classmethod
    def from_metadata(cls, metadata: SkillMetadata) -> SkillInfo:
        """Create SkillInfo from SkillMetadata."""
        return cls(
            name=metadata.name,
            display_name=metadata.display_name,
            domain=metadata.domain,
            summary=metadata.summary,
            full_description=metadata.full_description,
            input_schema=metadata.input_schema,
            tools_used=list(metadata.tools_used),
            tier=metadata.tier,
            estimated_duration=metadata.estimated_duration,
        )


class ToolRegistry:
    """Registry of all available tools and skills for discovery."""

    def __init__(self):
        self._tools: dict[str, ToolInfo] = {}
        self._skills: dict[str, SkillInfo] = {}
        self._domains: dict[str, list[str]] = {}
        self._skill_domains: dict[str, list[str]] = {}

    def register(self, tool: ToolInfo) -> None:
        """Register a tool for discovery."""
        self._tools[tool.name] = tool
        if tool.domain not in self._domains:
            self._domains[tool.domain] = []
        self._domains[tool.domain].append(tool.name)

    def register_skill(self, skill: SkillInfo) -> None:
        """Register a skill for discovery."""
        self._skills[skill.name] = skill
        if skill.domain not in self._skill_domains:
            self._skill_domains[skill.domain] = []
        self._skill_domains[skill.domain].append(skill.name)

    def search(
        self,
        query: str,
        domain: str | None = None,
        resource_type: ResourceType | None = None,
        limit: int = 20,
    ) -> list[ToolInfo | SkillInfo]:
        """Search tools and skills by query and optional filters."""
        results: list[tuple[int, ToolInfo | SkillInfo]] = []
        query_lower = query.lower()

        # Search tools
        if resource_type is None or resource_type == ResourceType.TOOL:
            for name, tool in self._tools.items():
                if domain and tool.domain != domain:
                    continue

                score = 0
                if query_lower in name.lower():
                    score += 3
                if query_lower in tool.summary.lower():
                    score += 2
                if query_lower in tool.full_description.lower():
                    score += 1

                if score > 0:
                    results.append((score, tool))

        # Search skills
        if resource_type is None or resource_type == ResourceType.SKILL:
            for name, skill in self._skills.items():
                if domain and skill.domain != domain:
                    continue

                score = 0
                if query_lower in name.lower():
                    score += 3
                if query_lower in skill.display_name.lower():
                    score += 3
                if query_lower in skill.summary.lower():
                    score += 2
                if query_lower in skill.full_description.lower():
                    score += 1
                # Boost skills slightly to surface them when relevant
                if query_lower in "skill" or query_lower in "troubleshoot":
                    score += 1

                if score > 0:
                    results.append((score, skill))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results[:limit]]

    def get_domains(self, include_skills: bool = True) -> dict[str, dict[str, int]]:
        """Get all domains with tool and skill counts."""
        domain_info: dict[str, dict[str, int]] = {}

        # Count tools per domain
        for domain, tools in self._domains.items():
            if domain not in domain_info:
                domain_info[domain] = {"tools": 0, "skills": 0}
            domain_info[domain]["tools"] = len(tools)

        # Count skills per domain
        if include_skills:
            for domain, skills in self._skill_domains.items():
                if domain not in domain_info:
                    domain_info[domain] = {"tools": 0, "skills": 0}
                domain_info[domain]["skills"] = len(skills)

        return domain_info

    def get_domain_tools(self, domain: str) -> list[ToolInfo]:
        """Get all tools in a domain."""
        return [
            self._tools[name]
            for name in self._domains.get(domain, [])
        ]

    def get_domain_skills(self, domain: str) -> list[SkillInfo]:
        """Get all skills in a domain."""
        return [
            self._skills[name]
            for name in self._skill_domains.get(domain, [])
        ]

    def get_tool(self, name: str) -> ToolInfo | None:
        """Get tool by exact name."""
        return self._tools.get(name)

    def get_skill(self, name: str) -> SkillInfo | None:
        """Get skill by exact name."""
        return self._skills.get(name)

    def list_skills(self, domain: str | None = None) -> list[SkillInfo]:
        """List all registered skills, optionally filtered by domain."""
        if domain:
            return self.get_domain_skills(domain)
        return list(self._skills.values())


# Global singleton
tool_registry = ToolRegistry()


def auto_register_tool(
    name: str,
    domain: str,
    func: Any = None,
    annotations: dict = None,
    tier: int = 2,
    summary: str = None,
    description: str = None,
    input_schema: dict = None,
) -> None:
    """Auto-register a tool in the discovery registry.

    Args:
        name: Tool name (e.g., 'oci_compute_list_instances')
        domain: Domain name (e.g., 'compute', 'cost')
        func: The tool function (optional - can be FunctionTool or callable)
        annotations: Optional MCP tool annotations
        tier: Performance tier (1-4), default 2
        summary: Optional summary override (if not extracted from func)
        description: Optional description override
        input_schema: Optional input schema override
    """
    import inspect

    # Try to extract the underlying function from FunctionTool wrapper
    actual_func = None
    docstring = ""
    extracted_schema = {}

    if func is not None:
        # Try to get the underlying function if wrapped by FastMCP
        if hasattr(func, 'fn'):
            actual_func = func.fn
        elif hasattr(func, '_fn'):
            actual_func = func._fn
        elif hasattr(func, '__wrapped__'):
            actual_func = func.__wrapped__
        elif callable(func):
            actual_func = func

        # Extract docstring
        if actual_func is not None:
            docstring = actual_func.__doc__ or ""
        elif hasattr(func, '__doc__'):
            docstring = func.__doc__ or ""

        # Try to get input schema from function signature
        if actual_func is not None:
            try:
                sig = inspect.signature(actual_func)
                for param_name, param in sig.parameters.items():
                    if param_name in ("self", "ctx"):
                        continue
                    if hasattr(param.annotation, "model_json_schema"):
                        extracted_schema = param.annotation.model_json_schema()
                        break
            except (ValueError, TypeError):
                pass  # Could not extract signature

    # Use provided values or extracted values
    final_summary = summary or (docstring.split("\n")[0] if docstring else name)
    final_description = description or docstring
    final_schema = input_schema or extracted_schema

    tool_info = ToolInfo(
        name=name,
        domain=domain,
        summary=final_summary,
        full_description=final_description,
        input_schema=final_schema,
        annotations=annotations or {},
        tier=tier,
        examples=[]
    )
    tool_registry.register(tool_info)


def register_skill_from_metadata(metadata: SkillMetadata) -> None:
    """Register a skill in the tool registry from SkillMetadata."""
    skill_info = SkillInfo.from_metadata(metadata)
    tool_registry.register_skill(skill_info)


__all__ = [
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
]
