"""
Tool discovery implementation for progressive disclosure pattern.

Enables agents to explore available tools efficiently without loading
all definitions upfront.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DetailLevel(str, Enum):
    """Level of detail for tool discovery."""
    NAME_ONLY = "name_only"           # Just tool names
    SUMMARY = "summary"               # Names + one-line descriptions
    FULL = "full"                     # Complete schema and documentation


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
    domain: Optional[str] = Field(
        default=None,
        description="Filter by domain: cost, compute, database, network, security, observability"
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


class ToolRegistry:
    """Registry of all available tools for discovery."""
    
    def __init__(self):
        self._tools: dict[str, ToolInfo] = {}
        self._domains: dict[str, list[str]] = {}
    
    def register(self, tool: ToolInfo) -> None:
        """Register a tool for discovery."""
        self._tools[tool.name] = tool
        if tool.domain not in self._domains:
            self._domains[tool.domain] = []
        self._domains[tool.domain].append(tool.name)
    
    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 20
    ) -> list[ToolInfo]:
        """Search tools by query and optional domain filter."""
        results = []
        query_lower = query.lower()
        
        for name, tool in self._tools.items():
            if domain and tool.domain != domain:
                continue
            
            # Score based on match location
            score = 0
            if query_lower in name.lower():
                score += 3
            if query_lower in tool.summary.lower():
                score += 2
            if query_lower in tool.full_description.lower():
                score += 1
            
            if score > 0:
                results.append((score, tool))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [tool for _, tool in results[:limit]]
    
    def get_domains(self) -> dict[str, int]:
        """Get all domains with tool counts."""
        return {domain: len(tools) for domain, tools in self._domains.items()}
    
    def get_domain_tools(self, domain: str) -> list[ToolInfo]:
        """Get all tools in a domain."""
        return [
            self._tools[name]
            for name in self._domains.get(domain, [])
        ]
    
    def get_tool(self, name: str) -> Optional[ToolInfo]:
        """Get tool by exact name."""
        return self._tools.get(name)


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


__all__ = [
    "DetailLevel",
    "SearchToolsInput",
    "ListDomainsInput",
    "ToolInfo",
    "ToolRegistry",
    "tool_registry",
    "auto_register_tool",
]
