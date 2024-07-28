import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

# Now import the required modules
from src.api.routes import bp
from src.core.model_repository import upload_model, download_model, get_metadata, validate_version

import json
from unittest import TestCase
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask

class TestModelRepository(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mock_ipfs_client = MagicMock()
        cls.mock_ipfs_patcher = patch('src.core.model_repository.upload.IPFSClient', return_value=cls.mock_ipfs_client)
        cls.mock_ipfs_patcher.start()

        cls.app = Flask(__name__)
        cls.app.register_blueprint(bp)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.mock_ipfs_patcher.stop()

    def test_upload_model(self):
        mock_model_data = b'mock_model_data'
        mock_metadata = {
            'models': {},
            'version': '1.0'
        }
        mock_updated_metadata = {
            'models': {
                'test_model': {
                    'versions': {
                        '1.0': 'mock_manifest_cid'
                    },
                    'latest_version': '1.0'
                }
            },
            'version': '1.0'
        }

        self.mock_ipfs_client.add_bytes.return_value = 'mock_model_cid'
        self.mock_ipfs_client.add_json.side_effect = ['mock_manifest_cid', 'mock_metadata_cid']
        self.mock_ipfs_client.get_json.side_effect = [mock_metadata, mock_updated_metadata]

        with patch('src.core.model_repository.upload.get_metadata', return_value=mock_metadata):
            result = upload_model('test_model', mock_model_data, '1.0')

        self.assertEqual(result, 'mock_manifest_cid')
        self.mock_ipfs_client.add_bytes.assert_called_once_with(mock_model_data)
        self.assertEqual(self.mock_ipfs_client.add_json.call_count, 2)
        self.assertEqual(self.mock_ipfs_client.get_json.call_count, 2)

    def test_download_model(self):
        mock_model_data = b'test_model_data'
        mock_manifest = {
            'model_id': 'test_model',
            'version': '1.0',
            'model_cid': 'mock_model_cid'
        }
        
        self.mock_ipfs_client.get_json.return_value = mock_manifest
        self.mock_ipfs_client.cat.return_value = mock_model_data

        with patch('src.core.model_repository.download.get_manifest_cid', return_value='mock_manifest_cid'):
            with patch('src.core.model_repository.download.IPFSClient', return_value=self.mock_ipfs_client):
                result = download_model('test_model', '1.0')
        
        print(f"Mock IPFS client get_json called: {self.mock_ipfs_client.get_json.called}")
        print(f"Mock IPFS client cat called: {self.mock_ipfs_client.cat.called}")
        print(f"Mock IPFS client get_json call count: {self.mock_ipfs_client.get_json.call_count}")
        print(f"Mock IPFS client cat call count: {self.mock_ipfs_client.cat.call_count}")
        
        self.assertEqual(result, mock_model_data)
        self.mock_ipfs_client.get_json.assert_called_once_with('mock_manifest_cid')
        self.mock_ipfs_client.cat.assert_called_once_with('mock_model_cid')

    def test_get_metadata(self):
        mock_objects = [
            {'Hash': 'QmNWz9o8JH2YfSC8hEf5PFJgxuWsxJWfxbD9vqgYfjxePa', 'Type': 'recursive'},
            {'Hash': 'QmNsLBcDWDvp7spSCtigZRRffdXPPN7fDnx4ZvMCiQVEtn', 'Type': 'recursive'},
            {'Hash': 'QmP64s8fm7pmpuStdVEpq662ALJS5dpxQmevZcEggj34rX', 'Type': 'recursive'}
        ]
        
        mock_manifest_1 = {
            'model_id': 'model1',
            'version': '1.0'
        }
        mock_manifest_2 = {
            'model_id': 'model2',
            'version': '2.0'
        }
        
        with patch('src.core.model_repository.metadata.IPFSClient') as mock_ipfs_client:
            mock_ipfs_client.return_value.list_objects.return_value = mock_objects
            mock_ipfs_client.return_value.cat.side_effect = [
                json.dumps(mock_manifest_1),
                json.dumps(mock_manifest_2),
                '{"invalid": "json"}'  # This should be ignored
            ]

            result = get_metadata()
        
        expected_metadata = {
            'models': {
                'model1': {
                    'versions': {'1.0': 'QmNWz9o8JH2YfSC8hEf5PFJgxuWsxJWfxbD9vqgYfjxePa'},
                    'latest_version': '1.0'
                },
                'model2': {
                    'versions': {'2.0': 'QmNsLBcDWDvp7spSCtigZRRffdXPPN7fDnx4ZvMCiQVEtn'},
                    'latest_version': '2.0'
                }
            },
            'version': '1.0'
        }
        
        self.assertEqual(result, expected_metadata)
        mock_ipfs_client.return_value.list_objects.assert_called_once()
        self.assertEqual(mock_ipfs_client.return_value.cat.call_count, 3)

    def test_validate_version(self):
        mock_metadata = {
            'models': {
                'test_model': {
                    'versions': {
                        '1.0': 'mock_manifest_cid',
                        '1.1': 'mock_manifest_cid'
                    }
                }
            }
        }

        with patch('src.core.model_repository.version_management.get_metadata', return_value=mock_metadata):
            self.assertTrue(validate_version('test_model', '2.0'))
            self.assertTrue(validate_version('test_model', '1.2'))
            self.assertFalse(validate_version('test_model', '1.1'))
            self.assertFalse(validate_version('test_model', '1.0'))
            self.assertFalse(validate_version('test_model', '0.9'))
            self.assertTrue(validate_version('new_model', '1.0'))

if __name__ == '__main__':
    unittest.main()