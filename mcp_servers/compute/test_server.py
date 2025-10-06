"""Tests for compute MCP server."""

import pytest
from unittest.mock import patch, MagicMock

from .server import list_instances, start_instance, stop_instance, get_instance_metrics


class TestComputeTools:
    """Test suite for compute MCP server functions."""

    @patch('mcp_servers.compute.server.oci.core.ComputeClient')
    def test_list_instances(self, mock_compute):
        """Test successful instance listing."""
        mock_instance = MagicMock()
        mock_instance.id = 'ocid1.instance.oc1..example'
        mock_instance.display_name = 'test-instance'
        mock_instance.lifecycle_state = 'RUNNING'
        mock_instance.shape = 'VM.Standard.E2.1.Micro'
        mock_compute.return_value.list_instances.return_value.data = [mock_instance]

        result = list_instances()
        assert len(result) == 1
        assert result[0]['display_name'] == 'test-instance'

    @patch('mcp_servers.compute.server.oci.core.ComputeClient')
    def test_start_instance(self, mock_compute):
        """Test successful instance start."""
        mock_response = MagicMock()
        mock_response.data.lifecycle_state = 'STARTING'
        mock_compute.return_value.instance_action.return_value = mock_response

        with patch('mcp_servers.compute.server.allow_mutations', return_value=True):
            result = start_instance('ocid1.instance.oc1..example')
            assert result['status'] == 'STARTING'

    @patch('mcp_servers.compute.server.oci.core.ComputeClient')
    def test_stop_instance(self, mock_compute):
        """Test successful instance stop."""
        mock_response = MagicMock()
        mock_response.data.lifecycle_state = 'STOPPING'
        mock_compute.return_value.instance_action.return_value = mock_response

        with patch('mcp_servers.compute.server.allow_mutations', return_value=True):
            result = stop_instance('ocid1.instance.oc1..example')
            assert result['status'] == 'STOPPING'

    @patch('mcp_servers.compute.server.oci.monitoring.MonitoringClient')
    def test_get_instance_metrics(self, mock_monitoring):
        """Test successful instance metrics retrieval."""
        mock_datapoint = MagicMock()
        mock_datapoint.value = 50.0
        mock_metric = MagicMock()
        mock_metric.aggregated_datapoints = [mock_datapoint]
        mock_monitoring.return_value.summarize_metrics_data.return_value.data = [mock_metric]

        result = get_instance_metrics('ocid1.instance.oc1..example')
        assert 'average' in result
        assert result['average'] == 50.0

    def test_list_instances_no_instances(self):
        """Test listing instances when none exist."""
        with patch('mcp_servers.compute.server.oci.core.ComputeClient') as mock_compute:
            mock_compute.return_value.list_instances.return_value.data = []
            result = list_instances()
            assert len(result) == 0

    @pytest.fixture
    def mock_instance_response(self):
        """Fixture providing mock instance response."""
        mock_instance = MagicMock()
        mock_instance.id = 'ocid1.instance.oc1..fixture-test'
        mock_instance.display_name = 'fixture-test-instance'
        mock_instance.lifecycle_state = 'RUNNING'
        mock_instance.shape = 'VM.Standard.E4.Flex'
        mock_instance.shape_config = MagicMock(ocpus=2, memory_in_gbs=16)
        return mock_instance

    def test_list_instances_with_fixture(self, mock_instance_response):
        """Test instance listing using pytest fixture."""
        with patch('mcp_servers.compute.server.oci.core.ComputeClient') as mock_compute:
            mock_compute.return_value.list_instances.return_value.data = [mock_instance_response]
            result = list_instances()
            assert len(result) == 1
            assert result[0]['display_name'] == 'fixture-test-instance'

    def test_start_instance_mutations_disabled(self):
        """Test starting instance when mutations are disabled."""
        with patch('mcp_servers.compute.server.allow_mutations', return_value=False):
            result = start_instance('ocid1.instance.oc1..example')
            assert 'error' in result
            assert 'mutations disabled' in result['error'].lower()

    def test_stop_instance_mutations_disabled(self):
        """Test stopping instance when mutations are disabled."""
        with patch('mcp_servers.compute.server.allow_mutations', return_value=False):
            result = stop_instance('ocid1.instance.oc1..example')
            assert 'error' in result
            assert 'mutations disabled' in result['error'].lower()

    @pytest.mark.parametrize("lifecycle_state", ["STARTING", "PROVISIONING", "RUNNING", "STOPPING", "STOPPED"])
    def test_instance_lifecycle_states(self, lifecycle_state):
        """Test handling different instance lifecycle states."""
        with patch('mcp_servers.compute.server.oci.core.ComputeClient') as mock_compute:
            mock_instance = MagicMock()
            mock_instance.lifecycle_state = lifecycle_state
            mock_instance.display_name = 'test-instance'
            mock_compute.return_value.list_instances.return_value.data = [mock_instance]

            result = list_instances()
            assert len(result) == 1
            assert result[0]['lifecycle_state'] == lifecycle_state
