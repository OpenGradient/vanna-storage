import sys
import os
# Add the 'src' directory to sys.path to import modules from there
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import unittest
from unittest.mock import patch, MagicMock
import pickle
from model_repository import ModelRepository
import json

"""
Unit tests for the ModelRepository class.

This module contains test cases for the ModelRepository class, which handles
model storage and retrieval using IPFS. It uses unittest and mock objects to
simulate IPFS interactions.
"""

class MockJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for handling MagicMock objects during serialization.
    """
    def default(self, obj):
        if isinstance(obj, MagicMock):
            return str(obj)
        return super().default(obj)

def mock_json_dumps(obj, *args, **kwargs):
    """
    Mock implementation of json.dumps using MockJSONEncoder.
    
    Args:
        obj: The object to be serialized.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    
    Returns:
        str: JSON-encoded string representation of the object.
    """
    kwargs.pop('cls', None)  # Remove cls if it's already in kwargs
    return json.dumps(obj, cls=MockJSONEncoder, *args, **kwargs)

class TestModelRepository(unittest.TestCase):
    """
    Test suite for ModelRepository class.
    
    This class contains setup methods and individual test cases for various
    functionalities of the ModelRepository class.
    """
    @classmethod
    def setUpClass(cls):
        cls.mock_ipfs_patcher = patch('model_repository.ipfs_client', autospec=True)
        cls.mock_ipfs = cls.mock_ipfs_patcher.start()
        cls.mock_client = cls.mock_ipfs.return_value.__enter__.return_value
        
        cls.mock_metadata_cid = "mock_metadata_cid"
        cls.mock_metadata = json.dumps({})
        
        cls.mock_client.add_bytes.return_value = {'Hash': 'mock_model_hash'}
        cls.mock_client.add.return_value = {'Hash': 'mock_file_hash'}
        cls.mock_client.add_json.return_value = {'Hash': 'mock_manifest_cid'}
        cls.mock_client.cat.return_value = cls.mock_metadata
        
        # Initialize ModelRepository once for all tests
        cls.model_repo = ModelRepository()
        cls.model_repo.metadata_cid = cls.mock_metadata_cid
        
        # Mock the _initialize_metadata method to prevent multiple initializations
        cls.model_repo._initialize_metadata = MagicMock()

    def setUp(self):
        # Reset mocks and metadata for each test
        self.mock_client.reset_mock()
        self.model_id = "test_model"
        self.serialized_model = b"serialized_model_data"
        self.model_repo._get_metadata = lambda: {"test_model": {"1.0": "mock_manifest_cid"}}
        self.model_data = {"key": "value"}


    @classmethod
    def tearDownClass(cls):
        """
        Clean up test environment after all tests have run.
        """
        cls.mock_ipfs_patcher.stop()

    def test_upload_model(self):
        """
        Test the upload_model method of ModelRepository.
        
        Verifies that the method correctly uploads a model and returns
        the expected manifest CID.
        """
        # self.mock_client.add_bytes.reset_mock()
        version = "1.0"
        manifest_cid = self.model_repo.upload_model(self.model_id, self.serialized_model, version)
        self.assertEqual(manifest_cid, 'mock_manifest_cid')
        self.mock_client.add_bytes.assert_called_once()


    def test_download_model(self):
        """
        Test the download_model method of ModelRepository.
        
        Ensures that the method correctly retrieves a model given its ID
        and version.
        """
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
        """
        Test the validate_version method of ModelRepository.
        
        Checks if the method correctly validates new versions and rejects
        existing or invalid versions.
        """
        version1 = "1.0"
        version2 = "1.1"
        
        # Create a mock for the list_versions method
        with patch.object(self.model_repo, 'list_versions', return_value=["1.0"]) as mock_list_versions:
            self.assertFalse(self.model_repo.validate_version(self.model_id, version1))
            self.assertTrue(self.model_repo.validate_version(self.model_id, version2))
            self.assertFalse(self.model_repo.validate_version(self.model_id, "0.9"))

            # Verify that list_versions was called with the correct model_id
            mock_list_versions.assert_called_with(self.model_id)

    def test_add_model(self):
        """
        Test the add_model method of ModelRepository.
        
        Verifies that the method successfully adds a new version of an
        existing model.
        """
        self.model_repo.upload_model(self.model_id, self.serialized_model, "1.0")
        new_model_data = self.model_data.copy()
        new_model_data['version'] = '1.1'
        new_serialized_model = pickle.dumps(new_model_data)
        new_manifest_cid = self.model_repo.add_model(self.model_id, new_serialized_model, '1.1')
        self.assertIsNotNone(new_manifest_cid)

if __name__ == '__main__':
    unittest.main()