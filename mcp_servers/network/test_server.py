"""Tests for network MCP server."""

import pytest
from unittest.mock import patch, MagicMock

from .server import list_vcns, list_subnets, summarize_public_endpoints


class TestNetworkMCP:
    """Test suite for network MCP server functions."""

    @patch('mcp_servers.network.server.oci.pagination.list_call_get_all_results')
    def test_list_vcns_success(self, mock_list):
        """Test successful VCN listing."""
        mock_vcn = MagicMock()
        mock_vcn.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_vcn]

        result = list_vcns('test_compartment')
        assert result['ok'] is True
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == 'test_id'

    @patch('mcp_servers.network.server.oci.pagination.list_call_get_all_results')
    def test_list_subnets_success(self, mock_list):
        """Test successful subnet listing."""
        mock_subnet = MagicMock()
        mock_subnet.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_subnet]

        result = list_subnets('test_vcn')
        assert result['ok'] is True
        assert len(result['data']) == 1

    @patch('mcp_servers.network.server.oci.pagination.list_call_get_all_results')
    def test_summarize_public_endpoints_success(self, mock_list):
        """Test successful public endpoints summarization."""
        # Mock VCNs
        mock_vcn = MagicMock(id='test_vcn')
        mock_list.side_effect = [
            MagicMock(data=[mock_vcn]),  # list_vcns
            MagicMock(data=[MagicMock(prohibit_public_ip_on_vnic=False)]),  # list_subnets
            MagicMock(data=[MagicMock(ip_addresses=[MagicMock(is_public=True)])])  # list_load_balancers
        ]

        result = summarize_public_endpoints('test_compartment')
        assert result['ok'] is True
        assert result['data']['public_subnets'] == 1
        assert result['data']['public_load_balancers'] == 1

    @patch('mcp_servers.network.server.oci.pagination.list_call_get_all_results')
    def test_list_vcns_failure(self, mock_list):
        """Test VCN listing failure handling."""
        mock_list.side_effect = Exception("API Error")
        with pytest.raises(Exception, match="API Error"):
            list_vcns('test_compartment')

    def test_list_vcns_empty_compartment(self):
        """Test listing VCNs for empty compartment."""
        with patch('mcp_servers.network.server.oci.pagination.list_call_get_all_results') as mock_list:
            mock_list.return_value.data = []
            result = list_vcns('empty_compartment')
            assert result['ok'] is True
            assert len(result['data']) == 0

    @pytest.fixture
    def mock_vcn_response(self):
        """Fixture providing mock VCN response."""
        mock_vcn = MagicMock()
        mock_vcn.__dict__ = {
            'id': 'ocid1.vcn.oc1..test',
            'display_name': 'test-vcn',
            'cidr_block': '10.0.0.0/16'
        }
        return mock_vcn

    def test_list_vcns_with_fixture(self, mock_vcn_response):
        """Test VCN listing using pytest fixture."""
        with patch('mcp_servers.network.server.oci.pagination.list_call_get_all_results') as mock_list:
            mock_list.return_value.data = [mock_vcn_response]
            result = list_vcns('test_compartment')
            assert result['ok'] is True
            assert result['data'][0]['display_name'] == 'test-vcn'
