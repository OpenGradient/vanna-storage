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

    def test_upload_model(self):
        mock_file = MagicMock()
        mock_file.filename = 'test_model.onnx'
        mock_file.read.return_value = b'mock_model_data'
        self.mock_ipfs_client.add_bytes.return_value = 'mock_model_cid'
        self.mock_ipfs_client.add_json.return_value = 'mock_manifest_cid'
        self.mock_ipfs_client.list_objects.return_value = []

        result, new_version = self.repo.upload_model('test_model', mock_file)
        self.assertEqual(result, 'mock_manifest_cid')
        self.assertEqual(new_version, '1.00')

        self.mock_ipfs_client.add_bytes.assert_called_with(b'mock_model_data')
        self.mock_ipfs_client.add_json.assert_called_once()

    def test_download_model(self):
        mock_model_data = b'test_model_data'
        mock_manifest = {
            'model_id': 'test_model',
            'version': '1.00',
            'model_file_cid': 'mock_model_cid'
        }

        self.mock_ipfs_client.get_json.return_value = mock_manifest
        self.mock_ipfs_client.cat.return_value = mock_model_data
        self.repo.get_manifest_cid = MagicMock(return_value='mock_manifest_cid')

        result = self.repo.download_model('test_model', '1.00')
        
        self.assertEqual(result, mock_model_data)
        self.mock_ipfs_client.get_json.assert_called_once_with('mock_manifest_cid')
        self.mock_ipfs_client.cat.assert_called_once_with('mock_model_cid')

    def test_list_versions(self):
        mock_objects = [
            {'Hash': 'cid1'},
            {'Hash': 'cid2'},
            {'Hash': 'cid3'}
        ]
        mock_manifests = [
            {'model_id': 'test_model', 'version': '1.00'},
            {'model_id': 'test_model', 'version': '1.01'},
            {'model_id': 'other_model', 'version': '1.00'}
        ]

        self.mock_ipfs_client.list_objects.return_value = mock_objects
        self.mock_ipfs_client.cat.side_effect = [json.dumps(manifest) for manifest in mock_manifests]

        versions = self.repo.list_versions('test_model')
        self.assertEqual(set(versions), {'1.00', '1.01'})

    def test_get_all_latest_models(self):
        mock_objects = [
            {'Hash': 'cid1'},
            {'Hash': 'cid2'},
            {'Hash': 'cid3'}
        ]
        mock_manifests = [
            {'model_id': 'model1', 'version': '1.00'},
            {'model_id': 'model1', 'version': '1.01'},
            {'model_id': 'model2', 'version': '1.00'}
        ]

        self.mock_ipfs_client.list_objects.return_value = mock_objects
        self.mock_ipfs_client.cat.side_effect = [json.dumps(manifest) for manifest in mock_manifests]

        latest_models = self.repo.get_all_latest_models()
        self.assertEqual(latest_models, {
            'model1': {'version': '1.01', 'cid': 'cid2'},
            'model2': {'version': '1.00', 'cid': 'cid3'}
        })

if __name__ == '__main__':
    unittest.main()