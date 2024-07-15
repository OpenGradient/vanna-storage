import sys
import os
import unittest
import pickle

# Add the 'src' directory to sys.path to import modules from there
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from model_repository import ModelRepository

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
        manifest_cid = self.model_repo.upload_model(self.model_id, self.serialized_model, "./test/test_text.txt")
        self.assertIsNotNone(manifest_cid)
        self.assertTrue(self.model_id in self.model_repo.models)

    def test_download_model(self):
        # Upload a model first
        version = "1.0"
        manifest_cid = self.model_repo.upload_model(self.model_id, self.serialized_model, version)

        # Now try to download it
        downloaded_model = self.model_repo.download_model(self.model_id, version)
        
        self.assertEqual(self.model_data, pickle.loads(downloaded_model))

    def test_validate_version(self):
        self.model_repo.upload_model(self.model_id, self.serialized_model)
        self.assertTrue(self.model_repo.validate_version(self.model_id, '1.1'))
        self.assertFalse(self.model_repo.validate_version(self.model_id, '1.0'))
        self.assertFalse(self.model_repo.validate_version('non_existent_model', '1.0'))

    def test_add_model(self):
        self.model_repo.upload_model(self.model_id, self.serialized_model, "1.0")
        new_model_data = self.model_data.copy()
        new_model_data['version'] = '1.1'
        new_serialized_model = pickle.dumps(new_model_data)
        new_manifest_cid = self.model_repo.add_model(self.model_id, new_serialized_model, '1.1')
        self.assertIsNotNone(new_manifest_cid)

if __name__ == '__main__':
    unittest.main()