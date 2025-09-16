import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from server import list_iam_users, list_groups, list_policies, list_cloud_guard_problems, list_data_safe_findings

class TestSecurityMCP(unittest.TestCase):

    @patch('server.oci.pagination.list_call_get_all_results')
    def test_list_iam_users_success(self, mock_list):
        mock_user = MagicMock()
        mock_user.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_user]
        
        result = list_iam_users('test_compartment')
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['data']), 1)
        self.assertEqual(result['data'][0]['id'], 'test_id')

    @patch('server.oci.pagination.list_call_get_all_results')
    def test_list_groups_success(self, mock_list):
        mock_group = MagicMock()
        mock_group.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_group]
        
        result = list_groups('test_compartment')
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['data']), 1)

    @patch('server.oci.pagination.list_call_get_all_results')
    def test_list_policies_success(self, mock_list):
        mock_policy = MagicMock()
        mock_policy.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_policy]
        
        result = list_policies('test_compartment')
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['data']), 1)

    @patch('server.oci.pagination.list_call_get_all_results')
    def test_list_cloud_guard_problems_success(self, mock_list):
        mock_problem = MagicMock()
        mock_problem.__dict__ = {'id': 'test_id'}
        mock_list.return_value.data = [mock_problem]
        
        result = list_cloud_guard_problems()
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['data']), 1)

    def test_list_data_safe_findings_stub(self):
        result = list_data_safe_findings()
        self.assertFalse(result['ok'])
        self.assertIn('NotImplemented', result['error'])

    @patch('server.oci.pagination.list_call_get_all_results')
    def test_list_iam_users_failure(self, mock_list):
        mock_list.side_effect = Exception("API Error")
        with self.assertRaises(Exception):
            list_iam_users('test_compartment')

if __name__ == '__main__':
    unittest.main()
