import sys
import os
# Add the 'src' directory to sys.path to import modules from there
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import unittest
from unittest.mock import patch, MagicMock
import pickle
from model_repository import ModelRepository
import json

class MockJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, MagicMock):
            return str(obj)
        return super().default(obj)

def mock_json_dumps(obj, *args, **kwargs):
    kwargs.pop('cls', None)  # Remove cls if it's already in kwargs
    return json.dumps(obj, cls=MockJSONEncoder, *args, **kwargs)

class TestModelRepository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_ipfs_patcher = patch('model_repository.ipfs_client')
        cls.mock_ipfs = cls.mock_ipfs_patcher.start()
        cls.mock_client = cls.mock_ipfs.return_value.__enter__.return_value
        
        cls.mock_metadata_cid = "mock_metadata_cid"
        cls.mock_metadata = json.dumps({})
        
        cls.mock_client.add_bytes.return_value = {'Hash': 'mock_model_hash'}
        cls.mock_client.add.return_value = {'Hash': 'mock_file_hash'}
        cls.mock_client.add_json.return_value = {'Hash': 'mock_manifest_cid'}
        cls.mock_client.cat.return_value = cls.mock_metadata
        
        cls.model_repo = ModelRepository()
        cls.model_repo.metadata_cid = cls.mock_metadata_cid

    @classmethod
    def tearDownClass(cls):
        cls.mock_ipfs_patcher.stop()

    def setUp(self):
        self.model_id = "test_model"
        self.serialized_model = b"serialized_model_data"
        self.model_repo = ModelRepository()
        self.model_repo.metadata_cid = "mock_metadata_cid"
        self.model_repo._get_metadata = lambda: {"test_model": {"1.0": "mock_manifest_cid"}}
        self.model_data = {"key": "value"}  # Add this line


    def test_upload_model(self):
        self.mock_client.add_bytes.reset_mock()
        version = "1.0"
        manifest_cid = self.model_repo.upload_model(self.model_id, self.serialized_model, version)
        self.assertEqual(manifest_cid, 'mock_manifest_cid')
        self.mock_client.add_bytes.assert_called_once()


    def test_download_model(self):
        version = "1.0"
        mock_manifest = json.dumps({
            "model_id": self.model_id,
            "version": version,
            "model_hash": "mock_model_hash"
        })
        with patch('model_repository.ipfs_client') as mock_ipfs:
            mock_client = mock_ipfs.return_value.__enter__.return_value
            mock_client.cat.side_effect = [mock_manifest, self.serialized_model]
            downloaded_model = self.model_repo.download_model(self.model_id, version)
        self.assertEqual(downloaded_model, self.serialized_model)

    def test_validate_version(self):
        version1 = "1.0"
        version2 = "1.1"
        self.model_repo.upload_model(self.model_id, self.serialized_model, version1)
        print(f"Existing versions: {self.model_repo.list_versions(self.model_id)}")
        self.assertFalse(self.model_repo.validate_version(self.model_id, version1))
        self.assertTrue(self.model_repo.validate_version(self.model_id, version2))
        self.assertFalse(self.model_repo.validate_version(self.model_id, "0.9"))

    def test_add_model(self):
        self.model_repo.upload_model(self.model_id, self.serialized_model, "1.0")
        new_model_data = self.model_data.copy()
        new_model_data['version'] = '1.1'
        new_serialized_model = pickle.dumps(new_model_data)
        new_manifest_cid = self.model_repo.add_model(self.model_id, new_serialized_model, '1.1')
        self.assertIsNotNone(new_manifest_cid)

if __name__ == '__main__':
    unittest.main()