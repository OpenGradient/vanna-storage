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
        
        self.mock_ipfs_client.add_bytes.return_value = 'mock_model_cid'
        self.mock_ipfs_client.add_json.return_value = 'QmSpjsQNVR6i3L9VTAME5Vso1h2RdEArJ3MztZWJF8f1cn'

        with patch('src.core.model_repository.upload.get_metadata', return_value={'models': {}}):
            with patch('src.core.model_repository.upload.IPFSClient', return_value=self.mock_ipfs_client):
                result = upload_model('test_model', mock_model_data, '1.0')
        
        print(f"Mock IPFS client add_bytes called: {self.mock_ipfs_client.add_bytes.called}")
        print(f"Mock IPFS client add_json called: {self.mock_ipfs_client.add_json.called}")
        print(f"Mock IPFS client add_bytes call count: {self.mock_ipfs_client.add_bytes.call_count}")
        print(f"Mock IPFS client add_json call count: {self.mock_ipfs_client.add_json.call_count}")
        
        self.assertTrue(result.startswith('Qm'))  # Check if the result is a valid CID
        self.assertEqual(len(result), 46)  # Check if the CID has the correct length
        self.mock_ipfs_client.add_bytes.assert_called_once_with(mock_model_data)
        self.mock_ipfs_client.add_json.assert_called()

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
        mock_metadata = {
            'models': {
                'test_model': {
                    'versions': {'1.0': 'mock_manifest_cid'},
                    'latest_version': '1.0'
                }
            },
            'version': '1.0'
        }
        
        with patch('src.core.model_repository.metadata.IPFSClient') as mock_ipfs_client:
            mock_ipfs_client.return_value.list_objects.return_value = [
                {'Hash': 'mock_manifest_cid'}
            ]
            mock_ipfs_client.return_value.cat.return_value = json.dumps({
                'model_id': 'test_model',
                'version': '1.0'
            })

            result = get_metadata()
        
        self.assertEqual(result, mock_metadata)
        mock_ipfs_client.return_value.list_objects.assert_called_once()
        mock_ipfs_client.return_value.cat.assert_called()

    def test_validate_version(self):
        mock_metadata = {'models': {'test_model': {'1.0': 'mock_manifest_cid'}}}
        
        with patch('src.core.model_repository.version_management.get_metadata', return_value=mock_metadata):
            result = validate_version('test_model', '2.0')
            self.assertTrue(result)

            result = validate_version('test_model', '0.9')
            self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()