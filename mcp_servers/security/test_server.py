"""Tests for security MCP server."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from .server import list_iam_users, list_groups, list_policies, list_cloud_guard_problems, list_data_safe_findings


class TestSecurityMCP:
    """Test suite for security MCP server functions."""

    @patch('mcp_servers.security.server.oci.pagination.list_call_get_all_results')
    def test_list_iam_users_success(self, mock_list):
        """Test successful IAM users listing."""
        mock_user = MagicMock()
        mock_user.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_user]

        result = list_iam_users('test_compartment')
        assert result['ok'] is True
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == 'test_id'

    @patch('mcp_servers.security.server.oci.pagination.list_call_get_all_results')
    def test_list_groups_success(self, mock_list):
        """Test successful groups listing."""
        mock_group = MagicMock()
        mock_group.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_group]

        result = list_groups('test_compartment')
        assert result['ok'] is True
        assert len(result['data']) == 1

    @patch('mcp_servers.security.server.oci.pagination.list_call_get_all_results')
    def test_list_policies_success(self, mock_list):
        """Test successful policies listing."""
        mock_policy = MagicMock()
        mock_policy.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_policy]

        result = list_policies('test_compartment')
        assert result['ok'] is True
        assert len(result['data']) == 1

    @patch('mcp_servers.security.server.oci.pagination.list_call_get_all_results')
    def test_list_cloud_guard_problems_success(self, mock_list):
        """Test successful Cloud Guard problems listing."""
        mock_problem = MagicMock()
        mock_problem.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_problem]

        result = list_cloud_guard_problems()
        assert result['ok'] is True
        assert len(result['data']) == 1

    def test_list_data_safe_findings_stub(self):
        """Test Data Safe findings stub implementation."""
        result = list_data_safe_findings()
        assert result['ok'] is False
        assert 'NotImplemented' in result['error']

    @patch('mcp_servers.security.server.oci.pagination.list_call_get_all_results')
    def test_list_iam_users_failure(self, mock_list):
        """Test IAM users listing failure handling."""
        mock_list.side_effect = Exception("API Error")
        with pytest.raises(Exception, match="API Error"):
            list_iam_users('test_compartment')

    def test_list_iam_users_empty_compartment(self):
        """Test listing IAM users for empty compartment."""
        with patch('mcp_servers.security.server.oci.pagination.list_call_get_all_results') as mock_list:
            mock_list.return_value.data = []
            result = list_iam_users('empty_compartment')
            assert result['ok'] is True
            assert len(result['data']) == 0

    @pytest.fixture
    def mock_user_response(self):
        """Fixture providing mock IAM user response."""
        mock_user = MagicMock()
        mock_user.__dict__ = {
            'id': 'ocid1.user.oc1..test',
            'name': 'test-user',
            'email': 'test@example.com',
            'is_mfa_activated': True,
            'time_created': datetime.now()
        }
        return mock_user

    def test_list_iam_users_with_fixture(self, mock_user_response):
        """Test IAM users listing using pytest fixture."""
        with patch('mcp_servers.security.server.oci.pagination.list_call_get_all_results') as mock_list:
            mock_list.return_value.data = [mock_user_response]
            result = list_iam_users('test_compartment')
            assert result['ok'] is True
            assert result['data'][0]['name'] == 'test-user'

    @pytest.mark.parametrize("error_type,error_message", [
        (ConnectionError, "Connection failed"),
        (TimeoutError, "Request timed out"),
        (ValueError, "Invalid parameter"),
    ])
    def test_list_iam_users_various_errors(self, error_type, error_message):
        """Test IAM users listing with various error types."""
        with patch('mcp_servers.security.server.oci.pagination.list_call_get_all_results') as mock_list:
            mock_list.side_effect = error_type(error_message)
            with pytest.raises(error_type, match=error_message):
                list_iam_users('test_compartment')
