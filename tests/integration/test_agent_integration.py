"""
Integration tests for mcp-oci servers using real OCI GenAI Agent

Tests all mcp-oci domain servers (cost, compute, network, etc.)
through the Agent interface.

Run with:
    cd /Users/abirzu/dev/MCP/mcp-oci
    pytest tests/integration/test_agent_integration.py -v

Prerequisites:
    - MCP HTTP Gateway running
    - MCP tools registered with Agent
    - Environment variables set
"""
import sys
from pathlib import Path

# Add shared test infrastructure
shared_infra_path = Path(__file__).parent.parent.parent.parent / "shared_test_infra"
sys.path.insert(0, str(shared_infra_path))
sys.path.insert(0, str(shared_infra_path / "tests"))

import pytest
import logging
from conftest import *

logger = logging.getLogger(__name__)


class TestCostServerIntegration:
    """Test oci-cost MCP server through Agent"""

    def test_daily_costs(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test daily cost query"""
        response = chat_helper(
            agent_session,
            "What were my OCI costs for the last 7 days?"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['cost', 'usd', '$', 'spend'])
        logger.info(f"✅ Daily costs: {response['text'][:200]}...")

    def test_service_breakdown(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test service cost breakdown"""
        response = chat_helper(
            agent_session,
            "Break down my OCI costs by service"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['service', 'compute', 'storage'])
        logger.info(f"✅ Service breakdown: {response['text'][:200]}...")

    def test_budget_status(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test budget status query"""
        response = chat_helper(
            agent_session,
            "What's the status of my OCI budgets?"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['budget', 'spend', 'track', 'none', 'no budget'])
        logger.info(f"✅ Budget status: {response['text'][:200]}...")


class TestComputeServerIntegration:
    """Test oci-compute MCP server through Agent"""

    def test_list_instances(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test listing compute instances"""
        response = chat_helper(
            agent_session,
            "List all compute instances in my compartment"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['instance', 'vm', 'compute', 'running', 'none', 'no instance'])
        logger.info(f"✅ Instance list: {response['text'][:200]}...")

    def test_instance_details(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test getting instance details"""
        response = chat_helper(
            agent_session,
            "Tell me about the compute instances and their shapes"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['shape', 'ocpu', 'memory', 'instance', 'none'])
        logger.info(f"✅ Instance details: {response['text'][:200]}...")


class TestNetworkServerIntegration:
    """Test oci-network MCP server through Agent"""

    def test_list_vcns(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test listing VCNs"""
        response = chat_helper(
            agent_session,
            "Show me all VCNs in my compartment"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['vcn', 'network', 'cidr', 'virtual', 'none'])
        logger.info(f"✅ VCN list: {response['text'][:200]}...")

    def test_network_overview(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test network overview"""
        response = chat_helper(
            agent_session,
            "Give me an overview of my OCI network configuration"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['network', 'vcn', 'subnet', 'security', 'none'])
        logger.info(f"✅ Network overview: {response['text'][:200]}...")


class TestSecurityServerIntegration:
    """Test oci-security MCP server through Agent"""

    def test_list_policies(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test listing IAM policies"""
        response = chat_helper(
            agent_session,
            "List the IAM policies in my compartment"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['policy', 'iam', 'permission', 'statement', 'none'])
        logger.info(f"✅ Policy list: {response['text'][:200]}...")

    def test_security_overview(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test security overview"""
        response = chat_helper(
            agent_session,
            "Give me an overview of my OCI security configuration"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['security', 'policy', 'user', 'group', 'access'])
        logger.info(f"✅ Security overview: {response['text'][:200]}...")


class TestDatabaseServerIntegration:
    """Test oci-db MCP server through Agent"""

    def test_list_databases(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test listing databases"""
        response = chat_helper(
            agent_session,
            "List all databases in my compartment"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['database', 'autonomous', 'db', 'mysql', 'none'])
        logger.info(f"✅ Database list: {response['text'][:200]}...")


class TestObservabilityServerIntegration:
    """Test oci-observability MCP server through Agent"""

    def test_monitoring_overview(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test monitoring overview"""
        response = chat_helper(
            agent_session,
            "What alarms are currently firing in my OCI environment?"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['alarm', 'monitor', 'alert', 'metric', 'none', 'no alarm'])
        logger.info(f"✅ Alarm status: {response['text'][:200]}...")


class TestInventoryServerIntegration:
    """Test oci-inventory MCP server through Agent"""

    def test_resource_summary(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test resource inventory summary"""
        response = chat_helper(
            agent_session,
            "Give me a summary of all OCI resources in my compartment"
        )

        response_text = response["text"].lower()
        assert any(word in response_text for word in ['resource', 'instance', 'database', 'vcn', 'inventory'])
        logger.info(f"✅ Inventory summary: {response['text'][:200]}...")


class TestCrossServerQueries:
    """Test queries that span multiple MCP servers"""

    def test_cost_and_compute_query(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test query that needs both cost and compute data"""
        response = chat_helper(
            agent_session,
            "Which of my compute instances are costing the most?"
        )

        response_text = response["text"].lower()
        # Should reference both compute and cost
        assert any(word in response_text for word in ['instance', 'compute', 'cost', 'none'])
        logger.info(f"✅ Cross-server query: {response['text'][:200]}...")

    def test_infrastructure_overview(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper
    ):
        """Test comprehensive infrastructure overview"""
        response = chat_helper(
            agent_session,
            "Give me a complete overview of my OCI infrastructure including compute, network, and costs"
        )

        assert len(response["text"]) > 0
        logger.info(f"✅ Infrastructure overview: {response['text'][:300]}...")


class TestParameterizedServerTests:
    """Parameterized tests for all servers"""

    @pytest.mark.parametrize("query,expected_words", [
        ("What are my OCI costs?", ["cost", "usd", "$", "spend"]),
        ("List my compute instances", ["instance", "vm", "compute", "none"]),
        ("Show my VCNs", ["vcn", "network", "none"]),
        ("What databases do I have?", ["database", "db", "none"]),
    ])
    def test_basic_queries(
        self,
        agent_runtime_client,
        agent_endpoint_id,
        agent_session,
        chat_helper,
        query,
        expected_words
    ):
        """Test basic queries for each domain"""
        response = chat_helper(agent_session, query)

        response_text = response["text"].lower()
        assert any(word in response_text for word in expected_words), \
            f"Response doesn't match expected: {response_text[:200]}"

        logger.info(f"✅ Query '{query[:30]}...' passed")


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
