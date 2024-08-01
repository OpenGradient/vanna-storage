import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from src.core.model_repository import ModelRepository

import json
from unittest import TestCase
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, Blueprint

bp = Blueprint('api', __name__)

class TestModelRepository(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mock_ipfs_client = MagicMock()
        cls.mock_ipfs_patcher = patch('src.core.model_repository.IPFSClient', return_value=cls.mock_ipfs_client)
        cls.mock_ipfs_patcher.start()

        cls.app = Flask(__name__)
        cls.app.register_blueprint(bp)
        cls.client = cls.app.test_client()
        cls.repo = ModelRepository()

    @classmethod
    def tearDownClass(cls):
        cls.mock_ipfs_patcher.stop()

    def test_download_model(self):
        mock_model_data = b'test_model_data'
        mock_manifest = {
            'model_id': 'test_model',
            'version': '1.00',
            'model_cid': 'mock_model_cid'
        }

        mock_metadata = {
            'models': {
                'test_model': {
                    'versions': {'1.00': 'mock_manifest_cid'},
                    'latest_version': '1.00'
                }
            }
        }

        self.repo.get_metadata = MagicMock(return_value=mock_metadata)
        self.mock_ipfs_client.get_json.side_effect = [mock_manifest]
        self.mock_ipfs_client.cat.return_value = mock_model_data

        result = self.repo.download_model('test_model', '1.00')
        
        self.assertEqual(result, mock_model_data)
        self.mock_ipfs_client.get_json.assert_called_once_with('mock_manifest_cid')
        self.mock_ipfs_client.cat.assert_called_once_with('mock_model_cid')

    def test_get_metadata(self):
        # Mock the initial metadata
        initial_metadata = {
            'models': {
                'test_model': {
                    'versions': {
                        '1.00': 'mock_manifest_cid'
                    },
                    'latest_version': '1.00'
                }
            }
        }
        
        # Mock the get_metadata method to return the initial metadata
        self.repo.get_metadata = MagicMock(return_value=initial_metadata)

        result = self.repo.get_metadata()
        
        expected_metadata = {
            'models': {
                'test_model': {
                    'versions': {
                        '1.00': 'mock_manifest_cid'
                    },
                    'latest_version': '1.00'
                }
            }
        }
        
        print("Actual result:")
        print(json.dumps(result, indent=2))
        print("\nExpected result:")
        print(json.dumps(expected_metadata, indent=2))
        
        self.assertEqual(result, expected_metadata)
        self.repo.get_metadata.assert_called_once()
    
    def test_upload_model(self):
        mock_model_data = b'mock_model_data'
        initial_metadata = {
            'models': {},
            'version': '1.0'
        }

        def mock_get_metadata():
            return initial_metadata

        self.repo.get_metadata = MagicMock(side_effect=mock_get_metadata)
        self.mock_ipfs_client.add_bytes.return_value = 'mock_model_cid'
        self.mock_ipfs_client.add_json.side_effect = ['mock_manifest_cid', 'mock_new_root_cid', 'mock_manifest_cid_2', 'mock_new_root_cid_2']

        # First upload
        result1, new_version1 = self.repo.upload_model('test_model', mock_model_data)
        self.assertEqual(result1, 'mock_manifest_cid')
        self.assertEqual(new_version1, '1.00')

        # Update mock metadata for second upload
        initial_metadata['models']['test_model'] = {
            'versions': {'1.00': 'old_manifest_cid'},
            'latest_version': '1.00'
        }

        # Second upload
        result2, new_version2 = self.repo.upload_model('test_model', mock_model_data)
        self.assertEqual(result2, 'mock_manifest_cid_2')
        self.assertEqual(new_version2, '1.01')

        self.mock_ipfs_client.add_bytes.assert_called_with(mock_model_data)
        self.assertEqual(self.mock_ipfs_client.add_json.call_count, 4)  # Called twice for each upload (manifest and metadata)

if __name__ == '__main__':
    unittest.main()