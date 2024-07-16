import sys
import os
# Add the 'src' directory to sys.path to import modules from there
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import unittest
from unittest.mock import patch, MagicMock
import pickle
from model_repository import ModelRepository
import json

class TestModelRepository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model_repo = ModelRepository()
        cls.model_repo.initialize_metadata()

    def setUp(self):
        self.model_id = "test_model"
        self.model_data = {"name": "Test Model", "version": "1.0"}
        self.serialized_model = pickle.dumps(self.model_data)

    def test_upload_model(self):
        version = "1.0"
        mock_model_hash = "mock_model_hash"
        mock_file_hash = "mock_file_hash"
        mock_manifest_cid = "mock_manifest_cid"
        mock_metadata_cid = "mock_metadata_cid"

        mock_metadata = json.dumps({})
        
        def mock_cat(cid):
            if cid == mock_metadata_cid:
                return mock_metadata
            return json.dumps({})

        with patch('model_repository.ipfs_client') as mock_ipfs_client:
            mock_client = mock_ipfs_client.return_value.__enter__.return_value
            mock_client.add_bytes.return_value = {'Hash': mock_model_hash}
            mock_client.add.return_value = {'Hash': mock_file_hash}
            mock_client.add_json.return_value = {'Hash': mock_manifest_cid}
            mock_client.cat.side_effect = mock_cat

            self.model_repo.metadata_cid = mock_metadata_cid

            manifest_cid = self.model_repo.upload_model(self.model_id, self.serialized_model, version, "./test/test_text.txt")

        self.assertEqual(manifest_cid, mock_manifest_cid)
        mock_client.add_bytes.assert_called_once()
        mock_client.add.assert_called_once_with("./test/test_text.txt")
        
        self.assertEqual(mock_client.add_json.call_count, 2)

        first_call_args = mock_client.add_json.call_args_list[0][0][0]
        self.assertEqual(first_call_args['model_id'], self.model_id)
        self.assertEqual(first_call_args['version'], version)
        self.assertIn('test_text.txt', first_call_args['files'])
        self.assertEqual(first_call_args['files']['test_text.txt'], 'mock_file_hash')
        self.assertEqual(first_call_args['model_hash'], 'mock_model_hash')

        second_call_args = mock_client.add_json.call_args_list[1][0][0]
        self.assertIn(self.model_id, second_call_args)
        self.assertIn(version, second_call_args)
        self.assertIn('mock_manifest_cid', second_call_args)

    def test_download_model(self):
        # Upload a model first
        version = "1.0"
        manifest_cid = self.model_repo.upload_model(self.model_id, self.serialized_model, version)

        # Now try to download it
        downloaded_model = self.model_repo.download_model(self.model_id, version)
        
        self.assertEqual(self.model_data, pickle.loads(downloaded_model))

    def test_validate_version(self):
        version = "1.0"
        self.model_repo.upload_model(self.model_id, self.serialized_model, version)
        
        self.assertTrue(self.model_repo.validate_version(self.model_id, '1.1'))
        self.assertFalse(self.model_repo.validate_version(self.model_id, '1.0'))
        self.assertFalse(self.model_repo.validate_version(self.model_id, '0.9'))
        self.assertTrue(self.model_repo.validate_version('non_existent_model', '1.0'))

    def test_add_model(self):
        self.model_repo.upload_model(self.model_id, self.serialized_model, "1.0")
        new_model_data = self.model_data.copy()
        new_model_data['version'] = '1.1'
        new_serialized_model = pickle.dumps(new_model_data)
        new_manifest_cid = self.model_repo.add_model(self.model_id, new_serialized_model, '1.1')
        self.assertIsNotNone(new_manifest_cid)

if __name__ == '__main__':
    unittest.main()