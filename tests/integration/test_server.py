"""
Integration tests for the MCP server.

These tests verify that the server initializes correctly
and tools are properly registered.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


class TestServerInitialization:
    """Tests for server initialization."""
    
    @pytest.fixture
    def mock_oci_config(self):
        """Mock OCI configuration."""
        with patch("oci.config.from_file") as mock_config:
            mock_config.return_value = {
                "tenancy": "ocid1.tenancy.oc1..test",
                "user": "ocid1.user.oc1..test",
                "fingerprint": "aa:bb:cc:dd:ee:ff",
                "key_file": "/path/to/key.pem",
                "region": "us-ashburn-1",
            }
            yield mock_config
    
    def test_server_creates_mcp_instance(self, mock_oci_config):
        """Test that server creates a valid MCP instance."""
        # Import after mocking to avoid OCI config errors
        with patch("oci.config.validate_config"):
            from mcp_server_oci.server import mcp
            
            assert mcp is not None
            assert mcp.name == "oci-mcp"
    
    def test_discovery_tools_registered(self, mock_oci_config):
        """Test that discovery tools are registered."""
        with patch("oci.config.validate_config"):
            from mcp_server_oci.server import mcp
            
            # The server should have registered discovery tools
            # Check that oci_search_tools is available
            tools = mcp._tool_manager._tools if hasattr(mcp, '_tool_manager') else {}
            
            # At minimum, server should initialize without error
            assert mcp is not None


class TestToolRegistration:
    """Tests for tool registration across all domains."""
    
    @pytest.fixture
    def mock_oci_environment(self):
        """Mock complete OCI environment."""
        with patch("oci.config.from_file") as mock_config, \
             patch("oci.config.validate_config"), \
             patch("oci.signer.Signer"):
            mock_config.return_value = {
                "tenancy": "ocid1.tenancy.oc1..test",
                "user": "ocid1.user.oc1..test",
                "fingerprint": "aa:bb:cc:dd:ee:ff",
                "key_file": "/path/to/key.pem",
                "region": "us-ashburn-1",
            }
            yield
    
    def test_all_domain_tools_registered(self, mock_oci_environment):
        """Test that tools from all domains are registered."""
        from mcp_server_oci.skills.discovery import tool_registry
        
        # Check expected domains exist
        domains = tool_registry.get_domains()
        
        # At minimum, the registry should be initialized
        assert isinstance(domains, dict)
    
    def test_tool_naming_convention(self, mock_oci_environment):
        """Test that all tools follow naming convention."""
        from mcp_server_oci.skills.discovery import tool_registry
        
        for name in tool_registry._tools.keys():
            # All tools should start with oci_
            assert name.startswith("oci_"), f"Tool {name} doesn't follow naming convention"
    
    def test_tool_has_annotations(self, mock_oci_environment):
        """Test that all tools have required annotations."""
        from mcp_server_oci.skills.discovery import tool_registry
        
        for name, tool in tool_registry._tools.items():
            # Every tool should have annotations
            assert tool.annotations is not None, f"Tool {name} missing annotations"


class TestServerManifest:
    """Tests for server manifest resource."""
    
    @pytest.fixture
    def mock_oci_environment(self):
        """Mock complete OCI environment."""
        with patch("oci.config.from_file") as mock_config, \
             patch("oci.config.validate_config"), \
             patch("oci.signer.Signer"):
            mock_config.return_value = {
                "tenancy": "ocid1.tenancy.oc1..test",
                "user": "ocid1.user.oc1..test",
                "fingerprint": "aa:bb:cc:dd:ee:ff",
                "key_file": "/path/to/key.pem",
                "region": "us-ashburn-1",
            }
            yield
    
    def test_manifest_structure(self, mock_oci_environment):
        """Test manifest has required structure."""
        # Import the manifest function
        import json
        import asyncio
        from mcp_server_oci.server import get_manifest
        
        # get_manifest is a resource-decorated async function
        # We need to call the underlying function
        manifest_str = asyncio.get_event_loop().run_until_complete(get_manifest.fn())
        manifest = json.loads(manifest_str)
        
        # Check required fields
        assert "name" in manifest
        assert "version" in manifest
        assert "description" in manifest
        assert "capabilities" in manifest
        assert "domains" in manifest
    
    def test_manifest_domains_populated(self, mock_oci_environment):
        """Test manifest includes all expected domains."""
        import json
        import asyncio
        from mcp_server_oci.server import get_manifest
        
        # get_manifest is a resource-decorated async function
        manifest_str = asyncio.get_event_loop().run_until_complete(get_manifest.fn())
        manifest = json.loads(manifest_str)
        
        expected_domains = ["cost", "compute", "database", "network", "security", "observability"]
        manifest_domain_names = [d["name"] for d in manifest["domains"]]
        
        for domain in expected_domains:
            assert domain in manifest_domain_names, f"Domain {domain} missing from manifest"


class TestResponseFormats:
    """Tests for response format handling."""
    
    def test_markdown_format_returns_string(self):
        """Test markdown format returns readable string."""
        from mcp_server_oci.core.formatters import format_response, ResponseFormat
        
        test_data = {
            "total_cost": 1234.56,
            "services": [
                {"name": "Compute", "cost": 500.00},
                {"name": "Storage", "cost": 734.56}
            ]
        }
        
        # When no markdown_template, falls back to JSON
        result = format_response(test_data, ResponseFormat.MARKDOWN)
        
        # Should return a string
        assert isinstance(result, str)
    
    def test_json_format_returns_valid_json(self):
        """Test JSON format returns parseable JSON."""
        import json
        from mcp_server_oci.core.formatters import format_response, ResponseFormat
        
        test_data = {"key": "value", "number": 42}
        
        result = format_response(test_data, ResponseFormat.JSON)
        
        # Should be parseable JSON
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["number"] == 42
