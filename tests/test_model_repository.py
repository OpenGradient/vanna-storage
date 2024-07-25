import sys
import os
import unittest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import unittest
from unittest import TestCase
from unittest.mock import patch, MagicMock
import json
from io import BytesIO
from app import create_app
from core.model_repository import ModelRepository

class TestModelRepository(TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a mock IPFSClient class
        cls.mock_ipfs_client = MagicMock()
        cls.mock_ipfs_client.__enter__ = MagicMock(return_value=cls.mock_ipfs_client)
        cls.mock_ipfs_client.__exit__ = MagicMock(return_value=None)

        # Set up mock return values for IPFSClient methods
        cls.mock_ipfs_client.add_bytes.return_value = {'Hash': 'mock_model_cid'}
        cls.mock_ipfs_client.add.return_value = {'Hash': 'mock_file_hash'}
        cls.mock_ipfs_client.add_json.return_value = {'Hash': 'mock_manifest_cid'}
        cls.mock_ipfs_client.cat.return_value = json.dumps({})

        # Patch the IPFSClient
        cls.mock_ipfs_patcher = patch('core.ipfs_client.IPFSClient', return_value=cls.mock_ipfs_client)
        cls.mock_ipfs_patcher.start()

        # Initialize ModelRepository once for all tests
        cls.model_repo = ModelRepository()
        cls.model_repo.metadata_cid = "mock_metadata_cid"

        cls.mock_ipfs_patcher.return_value = cls.model_repo
       
        # Mock the _initialize_metadata method to prevent multiple initializations
        cls.model_repo._initialize_metadata = MagicMock()

        # Create the Flask app
        cls.app = create_app()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.mock_ipfs_patcher.stop()

    def test_download_model(self):
        with self.app.app_context():
            # First, upload the model to ensure it exists in the metadata
            upload_response = self.client.post('/upload_model', data={
                'file': (BytesIO(b'test_model_data'), 'test_model.pkl'),
                'model_id': 'test_model',
                'version': '1.0'
            })
            self.assertEqual(upload_response.status_code, 200)

            # Now proceed to download the model
            with patch('core.ipfs_client.IPFSClient') as mock_ipfs_client, \
                patch.object(self.model_repo, 'get_manifest_cid', return_value='mock_manifest_cid'):
                mock_ipfs_client.return_value.__enter__.return_value.get_json.return_value = {'model_cid': 'mock_model_cid'}
                mock_ipfs_client.return_value.__enter__.return_value.cat.return_value = b'test_model_data'  # Match the uploaded data
                
                response = self.client.get('/download_model', query_string={'model_id': 'test_model', 'version': '1.0'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b'test_model_data')  # Expect the original uploaded data

    def test_download_model_missing_data(self):
        response = self.client.get('/download_model')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing model_id or version', json.loads(response.data)['error'])
    
    def test_get_latest_version(self):
        with self.app.app_context():
            # First, upload the model to ensure it exists in the metadata
            upload_response = self.client.post('/upload_model', data={
                'file': (BytesIO(b'test_model_data'), 'test_model.pkl'),
                'model_id': 'test_model',
                'version': '1.1'
            })
            self.assertEqual(upload_response.status_code, 200)

            # Now mock the list_versions method to return a version for the test_model
            with patch.object(self.model_repo, 'list_versions', return_value=['1.0', '1.1']):
                response = self.client.get('/get_latest_version/test_model')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(json.loads(response.data), {'latest_version': '1.1'})  # Expecting '1.1'

    def test_get_latest_version_not_found(self):
        with self.app.app_context():
            with patch.object(self.model_repo, 'get_latest_version', side_effect=ValueError("No versions found")):
                response = self.client.get('/get_latest_version/non_existent_model')
                self.assertEqual(response.status_code, 400)
                self.assertIn('No versions found', json.loads(response.data)['error'])

    def test_list_versions(self):
        with self.app.app_context():
            with patch.object(self.model_repo, 'list_versions', return_value=['1.0', '1.1']):
                response = self.client.get('/list_versions', query_string={'model_id': 'test_model'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(json.loads(response.data), ['1.0', '1.1'])
            
            with patch.object(self.model_repo, 'list_versions', side_effect=ValueError("No versions found")):
                response = self.client.get('/list_versions', query_string={'model_id': 'non_existent_model'})
                self.assertEqual(response.status_code, 404)
                self.assertEqual(json.loads(response.data), {"error": "No versions found for model_id: non_existent_model"})
                
    def test_list_versions_not_found(self):
        with self.app.app_context():
            with patch.object(self.model_repo, 'list_versions', side_effect=ValueError("No versions found")):
                response = self.client.get('/list_versions', query_string={'model_id': 'non_existent_model'})
                self.assertEqual(response.status_code, 404)
                self.assertEqual(json.loads(response.data), {"error": "No versions found for model_id: non_existent_model"})

    def test_upload_model(self):
        """
        Test the upload_model method of ModelRepository.
        
        Verifies that the method successfully uploads a model and returns
        the expected manifest CID.
        """
        with self.app.app_context():
            response = self.client.post('/upload_model', data={
                'file': (BytesIO(b'test_model_data'), 'test_model.pkl'),
                'model_id': 'test_model',
                'version': '1.0'
            })
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.data)
            self.assertIn('manifest_cid', response_data)
            self.assertTrue(isinstance(response_data['manifest_cid'], str))

    def test_upload_model_missing_data(self):
        response = self.client.post('/upload_model', data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing file, model_id, or version', json.loads(response.data)['error'])

    def test_validate_version(self):
        with self.app.app_context():
            # First, upload the model to ensure it exists in the metadata
            upload_response = self.client.post('/upload_model', data={
                'file': (BytesIO(b'test_model_data'), 'test_model.pkl'),
                'model_id': 'test_model',
                'version': '1.0'
            })
            self.assertEqual(upload_response.status_code, 200)

            # Mock the list_versions method to return a version for the test_model
            with patch.object(self.model_repo, 'list_versions', return_value=['1.0']):
                # Mock the validate_version method on the model_repo instance
                with patch.object(ModelRepository.get_instance(), 'validate_version', return_value=True) as mock_validate:
                    response = self.client.post('/validate_version', json={
                        'model_id': 'test_model',
                        'new_version': '1.1'  # Change to a new version to validate
                    })
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(json.loads(response.data), {'is_valid': True})
                    mock_validate.assert_called_once_with('test_model', '1.1')  # Check if it was called correctly
                    
    def test_validate_version_missing_data(self):
        response = self.client.post('/validate_version', json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing model_id or new_version', json.loads(response.data)['error'])

if __name__ == '__main__':
    unittest.main()