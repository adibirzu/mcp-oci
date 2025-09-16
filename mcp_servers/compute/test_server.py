import unittest
from unittest.mock import patch, MagicMock
from .server import list_instances, start_instance, stop_instance, get_instance_metrics

class TestComputeTools(unittest.TestCase):

    @patch('oci.core.ComputeClient')
    def test_list_instances(self, mock_compute):
        mock_instance = MagicMock()
        mock_instance.id = 'ocid1.instance.oc1..example'
        mock_instance.display_name = 'test-instance'
        mock_instance.lifecycle_state = 'RUNNING'
        mock_instance.shape = 'VM.Standard.E2.1.Micro'
        mock_compute.return_value.list_instances.return_value.data = [mock_instance]

        result = list_instances()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['display_name'], 'test-instance')

    @patch('oci.core.ComputeClient')
    def test_start_instance(self, mock_compute):
        mock_response = MagicMock()
        mock_response.data.lifecycle_state = 'STARTING'
        mock_compute.return_value.instance_action.return_value = mock_response

        with patch('server.allow_mutations', return_value=True):
            result = start_instance('ocid1.instance.oc1..example')
            self.assertEqual(result['status'], 'STARTING')

    @patch('oci.core.ComputeClient')
    def test_stop_instance(self, mock_compute):
        mock_response = MagicMock()
        mock_response.data.lifecycle_state = 'STOPPING'
        mock_compute.return_value.instance_action.return_value = mock_response

        with patch('server.allow_mutations', return_value=True):
            result = stop_instance('ocid1.instance.oc1..example')
            self.assertEqual(result['status'], 'STOPPING')

    @patch('oci.monitoring.MonitoringClient')
    def test_get_instance_metrics(self, mock_monitoring):
        mock_datapoint = MagicMock()
        mock_datapoint.value = 50.0
        mock_metric = MagicMock()
        mock_metric.aggregated_datapoints = [mock_datapoint]
        mock_monitoring.return_value.summarize_metrics_data.return_value.data = [mock_metric]

        result = get_instance_metrics('ocid1.instance.oc1..example')
        self.assertIn('average', result)
        self.assertEqual(result['average'], 50.0)

if __name__ == '__main__':
    unittest.main()
