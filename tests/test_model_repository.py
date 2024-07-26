import json
from unittest import TestCase
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from src.api.routes import bp
from src.core.model_repository import upload_model, download_model, get_metadata, validate_version

class TestModelRepository(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mock_ipfs_client = MagicMock()
        cls.mock_ipfs_patcher = patch('src.core.ipfs_client.IPFSClient', return_value=cls.mock_ipfs_client)
        cls.mock_ipfs_patcher.start()

        cls.app = Flask(__name__)
        cls.app.register_blueprint(bp)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.mock_ipfs_patcher.stop()

    def test_upload_model(self):
        mock_model_data = b'mock_model_data'
        mock_manifest_cid = 'mock_manifest_cid'
        
        self.mock_ipfs_client.add_bytes.return_value = 'mock_model_cid'
        self.mock_ipfs_client.add_json.return_value = mock_manifest_cid

        result = upload_model('test_model', mock_model_data, '1.0')
        
        self.assertEqual(result, mock_manifest_cid)
        self.mock_ipfs_client.add_bytes.assert_called_once_with(mock_model_data)
        self.mock_ipfs_client.add_json.assert_called()

    def test_download_model(self):
        mock_model_data = b'mock_model_data'
        mock_manifest = {
            'model_id': 'test_model',
            'version': '1.0',
            'model_cid': 'mock_model_cid'
        }
        
        self.mock_ipfs_client.get_json.return_value = mock_manifest
        self.mock_ipfs_client.cat.return_value = mock_model_data

        result = download_model('test_model', '1.0')
        
        self.assertEqual(result, mock_model_data)
        self.mock_ipfs_client.get_json.assert_called()
        self.mock_ipfs_client.cat.assert_called_with('mock_model_cid')

    def test_get_metadata(self):
        mock_metadata = {'models': {'test_model': {'1.0': 'mock_manifest_cid'}}}
        self.mock_ipfs_client.list_objects.return_value = [
            {'Hash': 'mock_manifest_cid'}
        ]
        self.mock_ipfs_client.cat.return_value = json.dumps({
            'model_id': 'test_model',
            'version': '1.0'
        })

        result = get_metadata()
        
        self.assertEqual(result, mock_metadata)
        self.mock_ipfs_client.list_objects.assert_called_once()
        self.mock_ipfs_client.cat.assert_called()

    def test_validate_version(self):
        mock_metadata = {'models': {'test_model': {'1.0': 'mock_manifest_cid'}}}
        
        with patch('src.core.model_repository.version_management.get_metadata', return_value=mock_metadata):
            result = validate_version('test_model', '2.0')
            self.assertTrue(result)

            result = validate_version('test_model', '0.9')
            self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()