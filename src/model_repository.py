import json
import os
from typing import Dict, List
from ipfs_client import ipfs_client
from packaging.version import parse  # Import the parse function here

# Assuming the existence of a config.py for storing configurations
from model_config import MODEL_FOLDER

class ModelRepository:
    @staticmethod
    def extract_hash(result):
        if isinstance(result, str):
            return result
        elif isinstance(result, dict) and 'Hash' in result:
            return result['Hash']
        elif hasattr(result, 'get'):
            return result.get('Hash', str(result))
        else:
            return str(result)
    
    """
    Manages storage and retrieval of model artifacts in IPFS.
    """
    def upload_model(self, model_id, serialized_model, *files):
        with ipfs_client() as client:
            manifest = {'model_id': model_id, 'version': '1.0', 'files': {}}
            
            # Add serialized model
            print("\nAdding serialized model")
            model_result = client.add_bytes(serialized_model)
            model_hash = self.extract_hash(model_result)
            manifest['model_hash'] = model_hash
            print(f"Model hash: {model_hash}")
            
            # Add additional files
            for file_path in files:
                print(f"\nTrying client.add({file_path})")
                file_result = client.add(file_path)
                file_hash = self.extract_hash(file_result)
                print(f"File hash: {file_hash}")
                manifest['files'][os.path.basename(file_path)] = file_hash
            
            print("\nCreating manifest JSON")
            manifest_json = json.dumps(manifest)
            print(f"Manifest JSON: {manifest_json}")
            
            print("\nAdding manifest to IPFS")
            manifest_result = client.add_json(manifest_json)
            manifest_cid = self.extract_hash(manifest_result)
            
            print(f"Uploaded model {model_id} version {manifest['version']} with manifest CID: {manifest_cid}")
            return manifest_cid


    def download_model(self, manifest_cid: str) -> Dict[str, str]:
        """
        Downloads model files based on the manifest CID and returns paths of downloaded files.
        """
        with ipfs_client() as client:
            manifest_data = client.cat(manifest_cid)
            manifest = json.loads(manifest_data)
            file_paths = {}
            for file_name, file_cid in manifest['files'].items():
                target_path = os.path.join(MODEL_FOLDER, manifest['model_id'], manifest['version'], file_name)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                client.get(file_cid, target=target_path)
                file_paths[file_name] = target_path
            print(f"Downloaded model {manifest['model_id']} version {manifest['version']}")
            return file_paths
 
    def add_model(self, model_id: str, serialized_model: bytes, new_version: str, *files) -> str:        
        """
        Adds a new version of an existing model to the repository.
        
        :param model_id: The ID of the existing model
        :param serialized_model: The serialized new version of the model
        :param new_version: The version string for the new model version
        :param files: Additional files to be included with the model
        :return: The CID of the new manifest
        """
        # Validate the new version
        if not self.validate_version(model_id, new_version):
            raise ValueError(f"Invalid version {new_version} for model {model_id}")

        with ipfs_client() as client:
            manifest = {'model_id': model_id, 'version': new_version, 'files': {}}
            
            # Add serialized model
            print(f"\nAdding serialized model for {model_id} version {new_version}")
            model_result = client.add_bytes(serialized_model)
            model_hash = self.extract_hash(model_result)
            manifest['model_hash'] = model_hash
            print(f"Model hash: {model_hash}")
            
            # Add additional files
            for file_path in files:
                print(f"\nAdding file: {file_path}")
                file_result = client.add(file_path)
                file_hash = self.extract_hash(file_result)
                print(f"File hash: {file_hash}")
                manifest['files'][os.path.basename(file_path)] = file_hash
            
            print("\nCreating manifest JSON")
            manifest_json = json.dumps(manifest)
            print(f"Manifest JSON: {manifest_json}")
            
            print("\nAdding manifest to IPFS")
            manifest_result = client.add_json(manifest_json)
            manifest_cid = self.extract_hash(manifest_result)
            
            print(f"Added new version of model {model_id} version {new_version} with manifest CID: {manifest_cid}")
            return manifest_cid

    def validate_version(self, model_id: str, new_version: str) -> bool:
        """
        Validates the new version against existing versions to ensure it follows the versioning scheme.
        """
        existing_versions = self.list_versions(model_id)
        if not existing_versions:
            return True  # No versions exist, so the new version is valid by default

        # Check if the new version is greater than all existing versions
        return all(parse(new_version) > parse(v) for v in existing_versions)

    def list_versions(self, model_id: str) -> List[str]:
        """
        Lists all available versions for a given model_id.
        """
        # Assuming MODEL_FOLDER is defined and points to the location where models are stored
        model_path = os.path.join(MODEL_FOLDER, model_id)
        try:
            versions = [d for d in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, d))]
            versions.sort(key=lambda v: parse(v))
            return versions
        except FileNotFoundError:
            print(f"No versions found for model_id {model_id}")
            return []

    def get_latest_version(self, model_id: str) -> str:
        """
        Retrieves the latest version of a model based on version numbers.
        """
        versions = self.list_versions(model_id)
        if not versions:
            raise ValueError(f"No versions available for model_id {model_id}")
        return versions[-1]  # Last version in the sorted list
    
    def validate_version(self, model_id: str, new_version: str) -> bool:
        """
        Validates the new version against existing versions to ensure it follows the versioning scheme.
        """
        existing_versions = self.list_versions(model_id)
        if not existing_versions:
            return True  # No versions exist, so the new version is valid by default

        # Check if the new version is greater than all existing versions
        return all(parse(new_version) > parse(v) for v in existing_versions)

    def list_versions(self, model_id: str) -> List[str]:
        """
        Lists all available versions for a given model_id.
        """
        # Assuming MODEL_FOLDER is defined and points to the location where models are stored
        model_path = os.path.join(MODEL_FOLDER, model_id)
        try:
            versions = [d for d in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, d))]
            versions.sort(key=lambda v: parse(v))
            return versions
        except FileNotFoundError:
            print(f"No versions found for model_id {model_id}")
            return []

    def get_latest_version(self, model_id: str) -> str:
        """
        Retrieves the latest version of a model based on version numbers.
        """
        versions = self.list_versions(model_id)
        if not versions:
            raise ValueError(f"No versions available for model_id {model_id}")
        return versions[-1]  # Last version in the sorted list