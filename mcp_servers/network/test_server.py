import unittest
from unittest.mock import patch, MagicMock
from server import list_vcns, list_subnets, summarize_public_endpoints

class TestNetworkMCP(unittest.TestCase):

    @patch('server.oci.pagination.list_call_get_all_results')
    def test_list_vcns_success(self, mock_list):
        mock_vcn = MagicMock()
        mock_vcn.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_vcn]
        
        result = list_vcns('test_compartment')
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['data']), 1)
        self.assertEqual(result['data'][0]['id'], 'test_id')

    @patch('server.oci.pagination.list_call_get_all_results')
    def test_list_subnets_success(self, mock_list):
        mock_subnet = MagicMock()
        mock_subnet.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_subnet]
        
        result = list_subnets('test_vcn')
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['data']), 1)

    @patch('server.oci.pagination.list_call_get_all_results')
    def test_summarize_public_endpoints_success(self, mock_list):
        # Mock VCNs
        mock_vcn = MagicMock(id='test_vcn')
        mock_list.side_effect = [
            MagicMock(data=[mock_vcn]),  # list_vcns
            MagicMock(data=[MagicMock(prohibit_public_ip_on_vnic=False)]),  # list_subnets
            MagicMock(data=[MagicMock(ip_addresses=[MagicMock(is_public=True)])])  # list_load_balancers
        ]
        
        result = summarize_public_endpoints('test_compartment')
        self.assertTrue(result['ok'])
        self.assertEqual(result['data']['public_subnets'], 1)
        self.assertEqual(result['data']['public_load_balancers'], 1)

    @patch('server.oci.pagination.list_call_get_all_results')
    def test_list_vcns_failure(self, mock_list):
        mock_list.side_effect = Exception("API Error")
        with self.assertRaises(Exception):
            list_vcns('test_compartment')

if __name__ == '__main__':
    unittest.main()
