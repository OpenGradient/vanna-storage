import sys
import os
# Add the 'src' directory to sys.path to import modules from there
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import unittest
from unittest.mock import patch, MagicMock
import pickle
from model_repository import ModelRepository
import json
from io import BytesIO
from app import app

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
        self.app = app.test_client()

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
        with patch.object(self.model_repo, 'upload_model', return_value='mock_manifest_cid'):
            response = self.app.post('/upload_model', data={
                'file': (BytesIO(b'test_model_data'), 'test_model.pkl'),
                'model_id': 'test_model',
                'version': '1.0'
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data), {'manifest_cid': 'mock_manifest_cid'})

    def test_upload_model_missing_data(self):
        response = self.app.post('/upload_model', data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing file, model_id, or version', json.loads(response.data)['error'])

    def test_add_model(self):
        """
        Test the add_model method of ModelRepository.
        
        Verifies that the method successfully adds a new version of an
        existing model.
        """
        with patch.object(self.model_repo, 'add_model', return_value='mock_manifest_cid'):
            response = self.app.post('/add_model', data={
                'file': (BytesIO(b'test_model_data'), 'test_model.pkl'),
                'model_id': 'test_model',
                'new_version': '1.1'
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data), {'manifest_cid': 'mock_manifest_cid'})

    def test_add_model_missing_data(self):
        response = self.app.post('/add_model', data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing file, model_id, or new_version', json.loads(response.data)['error'])

    def test_download_model(self):
        """
        Test the download_model method of ModelRepository.
        
        Ensures that the method correctly retrieves a model given its ID
        and version.
        """
        with patch.object(self.model_repo, 'download_model', return_value=b'test_model_data'):
            response = self.app.get('/download_model?model_id=test_model&version=1.0')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'test_model_data')

    def test_download_model_missing_data(self):
        response = self.app.get('/download_model')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing model_id or version', json.loads(response.data)['error'])

    def test_validate_version(self):
        """
        Test the validate_version method of ModelRepository.
        
        Checks if the method correctly validates new versions and rejects
        existing or invalid versions.
        """
        with patch.object(self.model_repo, 'validate_version', return_value=True):
            response = self.app.post('/validate_version', json={
                'model_id': 'test_model',
                'new_version': '1.1'
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data), {'is_valid': True})

    def test_validate_version_missing_data(self):
        response = self.app.post('/validate_version', json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing model_id or new_version', json.loads(response.data)['error'])

    def test_list_versions(self):
        """
        Test the list_versions method of ModelRepository.
        
        Verifies that the method correctly retrieves the list of versions
        for a given model ID.
        """
        with patch.object(self.model_repo, 'list_versions', return_value=['1.0', '1.1']):
            response = self.app.get('/list_versions/test_model')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data), {'versions': ['1.0', '1.1']})

    def test_list_versions_not_found(self):
        with patch.object(self.model_repo, 'list_versions', return_value=[]):
            response = self.app.get('/list_versions/non_existent_model')
            self.assertEqual(response.status_code, 404)
            self.assertIn('No versions found', json.loads(response.data)['error'])

    def test_get_latest_version(self):
        """
        Test the get_latest_version method of ModelRepository.
        
        Verifies that the method correctly retrieves the latest version
        for a given model ID.
        """
        with patch.object(self.model_repo, 'get_latest_version', return_value='1.1'):
            response = self.app.get('/get_latest_version/test_model')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data), {'latest_version': '1.1'})

    def test_get_latest_version_not_found(self):
        with patch.object(self.model_repo, 'get_latest_version', side_effect=FileNotFoundError):
            response = self.app.get('/get_latest_version/non_existent_model')
            self.assertEqual(response.status_code, 404)
            self.assertIn('Model not found', json.loads(response.data)['error'])

    def test_rollback_version(self):
        """
        Test the rollback_version method of ModelRepository.
        
        Verifies that the method correctly rolls back to a previous version
        of a model.
        """
        with patch.object(self.model_repo, 'rollback_version', return_value=True):
            response = self.app.post('/rollback_version', json={
                'model_id': 'test_model',
                'version': '1.0'
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data), {'success': True})

    def test_rollback_version_missing_data(self):
        response = self.app.post('/rollback_version', json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing model_id or version', json.loads(response.data)['error'])

    def test_rollback_version_not_found(self):
        with patch.object(self.model_repo, 'rollback_version', side_effect=FileNotFoundError):
            response = self.app.post('/rollback_version', json={
                'model_id': 'non_existent_model',
                'version': '1.0'
            })
            self.assertEqual(response.status_code, 404)
            self.assertIn('Model or version not found', json.loads(response.data)['error'])

if __name__ == '__main__':
    unittest.main()