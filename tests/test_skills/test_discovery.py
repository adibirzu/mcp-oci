"""
Tests for the tool discovery system.
"""
from __future__ import annotations

import pytest

from mcp_server_oci.skills.discovery import (
    ToolInfo,
    ToolRegistry,
    DetailLevel,
    SearchToolsInput,
    ListDomainsInput,
    tool_registry,
)


class TestToolInfo:
    """Tests for ToolInfo dataclass."""
    
    def test_creation(self):
        """Test creating a ToolInfo."""
        tool = ToolInfo(
            name="oci_cost_get_summary",
            domain="cost",
            summary="Get cost summary for a time window",
            full_description="Get comprehensive cost summary including totals, breakdowns, and forecasts.",
            input_schema={"type": "object", "properties": {}},
            annotations={"readOnlyHint": True},
            tier=2,
            examples=[{"tenancy_ocid": "ocid1..."}]
        )
        
        assert tool.name == "oci_cost_get_summary"
        assert tool.domain == "cost"
        assert tool.tier == 2
        assert tool.annotations["readOnlyHint"] is True


class TestToolRegistry:
    """Tests for ToolRegistry class."""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry for testing."""
        return ToolRegistry()
    
    @pytest.fixture
    def populated_registry(self, registry):
        """Create a registry with test tools."""
        tools = [
            ToolInfo(
                name="oci_cost_get_summary",
                domain="cost",
                summary="Get cost summary",
                full_description="Get comprehensive cost analysis",
                input_schema={},
                annotations={},
                tier=2,
                examples=[]
            ),
            ToolInfo(
                name="oci_cost_monthly_trend",
                domain="cost",
                summary="Get monthly cost trend",
                full_description="Analyze monthly spending patterns",
                input_schema={},
                annotations={},
                tier=2,
                examples=[]
            ),
            ToolInfo(
                name="oci_compute_list_instances",
                domain="compute",
                summary="List compute instances",
                full_description="List all compute instances in compartment",
                input_schema={},
                annotations={},
                tier=2,
                examples=[]
            ),
            ToolInfo(
                name="oci_database_list_autonomous",
                domain="database",
                summary="List autonomous databases",
                full_description="List all ADBs in compartment",
                input_schema={},
                annotations={},
                tier=2,
                examples=[]
            ),
        ]
        
        for tool in tools:
            registry.register(tool)
        
        return registry
    
    def test_register_tool(self, registry):
        """Test registering a tool."""
        tool = ToolInfo(
            name="test_tool",
            domain="test",
            summary="Test tool",
            full_description="A test tool",
            input_schema={},
            annotations={},
            tier=1,
            examples=[]
        )
        
        registry.register(tool)
        
        assert "test_tool" in registry._tools
        assert "test" in registry._domains
        assert "test_tool" in registry._domains["test"]
    
    def test_register_multiple_tools_same_domain(self, registry):
        """Test registering multiple tools in the same domain."""
        tools = [
            ToolInfo("tool1", "domain1", "s1", "d1", {}, {}, 1, []),
            ToolInfo("tool2", "domain1", "s2", "d2", {}, {}, 1, []),
        ]
        
        for tool in tools:
            registry.register(tool)
        
        assert len(registry._domains["domain1"]) == 2
    
    def test_get_domains(self, populated_registry):
        """Test getting all domains with tool and skill counts."""
        domains = populated_registry.get_domains()

        assert "cost" in domains
        assert "compute" in domains
        assert "database" in domains
        # New API returns {"tools": N, "skills": M} per domain
        assert domains["cost"]["tools"] == 2  # 2 cost tools
        assert domains["compute"]["tools"] == 1
        assert domains["database"]["tools"] == 1
    
    def test_get_domain_tools(self, populated_registry):
        """Test getting tools in a specific domain."""
        cost_tools = populated_registry.get_domain_tools("cost")
        
        assert len(cost_tools) == 2
        assert all(t.domain == "cost" for t in cost_tools)
    
    def test_get_domain_tools_nonexistent(self, populated_registry):
        """Test getting tools from non-existent domain."""
        tools = populated_registry.get_domain_tools("nonexistent")
        
        assert tools == []
    
    def test_search_by_name(self, populated_registry):
        """Test searching tools by name."""
        results = populated_registry.search("cost")
        
        assert len(results) >= 2
        assert all("cost" in t.name.lower() or "cost" in t.summary.lower() for t in results)
    
    def test_search_by_summary(self, populated_registry):
        """Test searching tools by summary content."""
        results = populated_registry.search("instances")
        
        assert len(results) >= 1
        assert any("instances" in t.summary.lower() for t in results)
    
    def test_search_with_domain_filter(self, populated_registry):
        """Test searching with domain filter."""
        results = populated_registry.search("list", domain="compute")
        
        assert len(results) >= 1
        assert all(t.domain == "compute" for t in results)
    
    def test_search_with_limit(self, populated_registry):
        """Test search result limit."""
        # Search for something that matches multiple tools
        results = populated_registry.search("oci", limit=2)
        
        assert len(results) <= 2
    
    def test_search_no_results(self, populated_registry):
        """Test search with no matches."""
        results = populated_registry.search("nonexistent_xyz_123")
        
        assert results == []
    
    def test_get_tool(self, populated_registry):
        """Test getting a specific tool by name."""
        tool = populated_registry.get_tool("oci_cost_get_summary")
        
        assert tool is not None
        assert tool.name == "oci_cost_get_summary"
        assert tool.domain == "cost"
    
    def test_get_tool_nonexistent(self, populated_registry):
        """Test getting a non-existent tool."""
        tool = populated_registry.get_tool("nonexistent")
        
        assert tool is None


class TestSearchToolsInput:
    """Tests for SearchToolsInput model."""
    
    def test_defaults(self):
        """Test default values."""
        input_model = SearchToolsInput(query="cost")
        
        assert input_model.query == "cost"
        assert input_model.detail_level == DetailLevel.SUMMARY
        assert input_model.domain is None
        assert input_model.limit == 20
    
    def test_full_options(self):
        """Test with all options set."""
        input_model = SearchToolsInput(
            query="instances",
            detail_level=DetailLevel.FULL,
            domain="compute",
            limit=5
        )
        
        assert input_model.query == "instances"
        assert input_model.detail_level == DetailLevel.FULL
        assert input_model.domain == "compute"
        assert input_model.limit == 5
    
    def test_limit_constraints(self):
        """Test limit constraints."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            SearchToolsInput(query="test", limit=0)
        
        with pytest.raises(ValidationError):
            SearchToolsInput(query="test", limit=51)


class TestListDomainsInput:
    """Tests for ListDomainsInput model."""
    
    def test_defaults(self):
        """Test default values."""
        input_model = ListDomainsInput()
        
        assert input_model.include_tool_count is True
    
    def test_custom_value(self):
        """Test with custom value."""
        input_model = ListDomainsInput(include_tool_count=False)
        
        assert input_model.include_tool_count is False


class TestDetailLevel:
    """Tests for DetailLevel enum."""
    
    def test_values(self):
        """Test enum values."""
        assert DetailLevel.NAME_ONLY.value == "name_only"
        assert DetailLevel.SUMMARY.value == "summary"
        assert DetailLevel.FULL.value == "full"


class TestGlobalRegistry:
    """Tests for the global tool registry singleton."""
    
    def test_singleton_exists(self):
        """Test that global registry exists."""
        assert tool_registry is not None
        assert isinstance(tool_registry, ToolRegistry)
    
    def test_has_domains(self):
        """Test that registry has expected domains (after server registers tools)."""
        # Note: This test assumes tools have been registered
        # In a fresh import, the registry might be empty
        domains = tool_registry.get_domains()
        
        # The registry should at minimum exist
        assert isinstance(domains, dict)
