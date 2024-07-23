import json
import os
import time
from typing import Dict, List
from ipfs_client import IPFSClient
from packaging.version import parse
import logging
import requests
from functools import wraps
import flask

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting decorator
def rate_limit(limit_seconds):
    def decorator(func):  
        last_called = 0
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal last_called
            elapsed = time.time() - last_called
            if elapsed < limit_seconds:
                raise ValueError(f"Rate limit exceeded. Please wait {limit_seconds - elapsed:.2f} seconds.")
            result = func(*args, **kwargs)
            last_called = time.time()
            return result
        return wrapper
    return decorator


class ModelRepository:
    """
    Manages the storage and retrieval of machine learning models using IPFS.

    This class provides functionality for uploading, downloading, and managing
    different versions of models, along with associated metadata.
    """

    def __init__(self):
        """
        Initializes the ModelRepository.
        """
        self.metadata_cid = None
        self.initialize_metadata()

    def initialize_metadata(self):
        client = IPFSClient()
        if not self.metadata_cid:
            initial_metadata = {"models": {}, "version": "1.0"}
            result = client.add_json(json.dumps(initial_metadata))
            self.metadata_cid = self.extract_hash(result)
            logging.info(f"Initialized new metadata with CID: {self.metadata_cid}")
        else:
            logging.info(f"Using existing metadata with CID: {self.metadata_cid}")

    @classmethod
    def get_instance(cls):
        """
        Returns a singleton instance of ModelRepository.
        """
        if not hasattr(flask.current_app, 'model_repo'):
            flask.current_app.model_repo = cls()
        return flask.current_app.model_repo

    def _get_metadata(self) -> Dict[str, Dict[str, str]]:
        client = IPFSClient()
        try:
            if not self.metadata_cid:
                logging.warning("No metadata CID found. Initializing new metadata.")
                return {"models": {}, "version": "1.0"}

            metadata_json = client.cat(self.metadata_cid)
            logging.info(f"Raw metadata from IPFS: {metadata_json}")
            
            metadata = json.loads(metadata_json)
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            logging.info(f"Parsed metadata: {metadata}")
            
            if not isinstance(metadata, dict):
                logging.error(f"Invalid metadata structure: {metadata}")
                return {"models": {}, "version": "1.0"}
            
            if 'models' not in metadata:
                metadata['models'] = {}
            
            # Ensure all model versions are under the 'models' key
            for key, value in list(metadata.items()):
                if key != 'models' and isinstance(value, dict):
                    if key not in metadata['models']:
                        metadata['models'][key] = {}
                    metadata['models'][key].update(value)
                    del metadata[key]
            
            logging.info(f"Structured metadata: {metadata}")
            return metadata
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {str(e)}")
            return {"models": {}, "version": "1.0"}
        except Exception as e:
            logging.error(f"Error getting metadata: {str(e)}")
            return {"models": {}, "version": "1.0"}

    def _store_metadata(self, new_metadata: Dict[str, Dict[str, str]]):
        client = IPFSClient()
        
        # Retrieve existing metadata
        existing_metadata = self._get_metadata()
        logging.info(f"Existing metadata: {existing_metadata}")
        
        # Ensure the correct structure
        if 'models' not in existing_metadata:
            existing_metadata['models'] = {}
        
        # Update existing metadata with new metadata
        for model_id, versions in new_metadata.get('models', {}).items():
            if model_id not in existing_metadata['models']:
                existing_metadata['models'][model_id] = {}
            existing_metadata['models'][model_id].update(versions)
        
        logging.info(f"Updated metadata before storage: {existing_metadata}")
        
        # Store updated metadata
        metadata_json = json.dumps(existing_metadata)
        logging.info(f"Metadata JSON to be stored: {metadata_json}")
        result = client.add_json(metadata_json)
        new_metadata_cid = self.extract_hash(result)
        logging.info(f"Storing updated metadata with CID: {new_metadata_cid}")
        
        # Verify stored metadata
        stored_metadata_json = client.cat(new_metadata_cid)
        logging.info(f"Raw stored metadata JSON: {stored_metadata_json}")
        
        try:
            stored_metadata = json.loads(json.loads(stored_metadata_json))
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding stored metadata: {e}")
            logging.error(f"Problematic JSON: {stored_metadata_json}")
            raise ValueError("Failed to decode stored metadata")
        
        logging.info(f"Decoded stored metadata: {stored_metadata}")
        
        # Compare metadata directly
        if stored_metadata != existing_metadata:
            logging.error(f"Stored metadata does not match updated metadata")
            logging.error(f"Stored: {json.dumps(stored_metadata)}")
            logging.error(f"Expected: {json.dumps(existing_metadata)}")
            raise ValueError("Metadata storage verification failed")
        
        self.metadata_cid = new_metadata_cid
        logging.info(f"Updated metadata_cid: {self.metadata_cid}")

    def _store_manifest_cid(self, model_id: str, version: str, manifest_cid: str):
        """
        Stores the manifest CID for a specific model and version in the metadata on IPFS.

        This method retrieves the existing metadata (if any) from IPFS, updates it with the
        new manifest CID for the specified model and version, and then stores the updated
        metadata back to IPFS. It includes error handling for parsing existing metadata
        and ensures the metadata is in the correct format before storing.

        Args:
            model_id (str): The unique identifier for the model.
            version (str): The version of the model.
            manifest_cid (str): The manifest CID to be stored.

        Raises:
            json.JSONDecodeError: If the existing metadata cannot be parsed as JSON.
            TypeError: If the existing metadata is not in the expected format.

        Note:
            This method is intended for internal use within the ModelRepository class.
            It updates the `self.metadata_cid` attribute with the new CID of the updated metadata.

        Example:
            >>> repo = ModelRepository()
            >>> repo._store_manifest_cid("model_123", "1.0", "QmA1b2C3d4E5f6G7h8I9j0K1L2m3N4o5P6q7R8s9T0u1V2w3X4y5Z")
        """
        client = IPFSClient()
        if self.metadata_cid:
            try:
                metadata_json = client.cat(self.metadata_cid)
                metadata = json.loads(metadata_json)
                print(f"Existing metadata: {metadata}")
            except (json.JSONDecodeError, TypeError):
                print(f"Warning: Could not parse existing metadata. Creating new metadata.")
                metadata = {}
        else:
            print("No existing metadata. Creating new metadata.")
            metadata = {}

        if not isinstance(metadata, dict):
            print(f"Warning: Existing metadata is not a dictionary. Creating new metadata.")
            metadata = {}

        if model_id not in metadata:
            metadata[model_id] = {}
        metadata[model_id][version] = manifest_cid

        print(f"Updated metadata: {metadata}")
        updated_metadata_json = json.dumps(metadata)
        result = client.add_json(updated_metadata_json)
        self.metadata_cid = self.extract_hash(result)
        print(f"New metadata CID: {self.metadata_cid}")

        # Verify stored metadata
        stored_metadata = json.loads(client.cat(self.metadata_cid))
        print(f"Verified stored metadata: {stored_metadata}")

    def get_manifest_cid(self, model_id: str, version: str) -> str:
        metadata = self._get_metadata()
        if 'models' in metadata and model_id in metadata['models'] and version in metadata['models'][model_id]:
            return metadata['models'][model_id][version]
        raise ValueError(f"No manifest found for model {model_id} version {version}")

    @staticmethod
    def extract_hash(result):
        """
        Extracts the hash value from various result formats returned by IPFS operations.

        This method handles different result structures, including strings, dictionaries,
        and objects with a 'get' method, to consistently return the hash value.

        Args:
            result: The result object from an IPFS operation, which can be a string,
                    dictionary, or an object with a 'get' method.

        Returns:
            str: The extracted hash value, or a string representation of the result
                if no hash could be extracted.
        """
        if isinstance(result, str):
            return result
        elif isinstance(result, dict) and 'Hash' in result:
            return result['Hash']
        elif hasattr(result, 'get'):
            return result.get('Hash', str(result))
        else:
            return str(result)
    
    def upload_model(self, model_id: str, serialized_model: bytes, version: str) -> str:
        """
        Uploads a model to IPFS or adds a new version of an existing model.

        Args:
            model_id (str): Unique identifier for the model.
            serialized_model (bytes): The serialized model data.
            version (str): Version string for the model.

        Returns:
            str: The CID of the uploaded model manifest.
        """
        logging.info(f"Uploading/Adding model: {model_id}, version: {version}")
        
        client = IPFSClient()
        model_cid = client.add_bytes(serialized_model)['Hash']
        logging.info(f"Uploaded model file with CID: {model_cid}")
        
        manifest = {
            "model_id": model_id,
            "version": version,
            "model_hash": model_cid
        }
        manifest_json = json.dumps(manifest)
        manifest_result = client.add_json(manifest_json)
        manifest_cid = self.extract_hash(manifest_result)
        logging.info(f"Created manifest with CID: {manifest_cid}")

        # Get existing metadata
        existing_metadata = self._get_metadata()
        logging.info(f"Existing metadata: {existing_metadata}")

        # Update metadata
        if 'models' not in existing_metadata:
            existing_metadata['models'] = {}
        if model_id not in existing_metadata['models']:
            existing_metadata['models'][model_id] = {}
        existing_metadata['models'][model_id][version] = manifest_cid

        # Store updated metadata
        self._store_metadata(existing_metadata)
        logging.info(f"Updated metadata for model {model_id} version {version}")

        return manifest_cid

    def download_model(self, model_id: str, version: str) -> bytes:
        """
        Downloads a specific version of a model from IPFS.

        Args:
            model_id (str): Unique identifier for the model.
            version (str): Version of the model to download.

        Returns:
            bytes: The serialized model data.

        Raises:
            ValueError: If the specified model version is not found.
        """
        client = IPFSClient()
        # Retrieve the manifest for the specified version
        manifest_cid = self.get_manifest_cid(model_id, version)
        if not manifest_cid:
            raise ValueError(f"No manifest found for model {model_id} version {version}")
        
        # Get the manifest content
        manifest = client.get_json(manifest_cid)
        
        # Get the model hash from the manifest
        model_hash = manifest['model_hash']
        
        # Download and return the model data
        model_data = client.cat(model_hash)
        return model_data
 
    def validate_version(self, model_id: str, new_version: str) -> bool:
        """
        Validates if a new version string is acceptable for a given model.

        Args:
            model_id (str): Unique identifier for the model.
            new_version (str): The new version string to validate.

        Returns:
            bool: True if the version is valid, False otherwise.
        """
        existing_versions = self.list_versions(model_id)
        if not existing_versions:
            return True
        return all(parse(new_version) > parse(v) for v in existing_versions)

    def list_versions(self, model_id: str) -> List[str]:
        """
        Lists all available versions for a given model_id.
        """
        metadata = self._get_metadata()
        if 'models' in metadata and model_id in metadata['models']:
            versions = list(metadata['models'][model_id].keys())
            versions.sort(key=lambda v: parse(v))
            return versions
        return []

    def get_latest_version(self, model_id: str) -> str:
        """
        Retrieves the latest version of a model based on version numbers.
        """
        versions = self.list_versions(model_id)
        if not versions:
            raise ValueError(f"No versions available for model_id {model_id}")
        return versions[-1]  # Last version in the sorted list