import json
from typing import Dict, List
from core.ipfs_client import IPFSClient
from packaging.version import parse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelRepository:
    """
    Manages the storage and retrieval of machine learning models using IPFS.

    This class provides functionality for uploading, downloading, and managing
    different versions of models, along with associated metadata.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._instance is not None:
            raise ValueError("An instantiation already exists!")
        self._instance = self
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

    def _get_metadata(self):
        client = IPFSClient()
        if not self.metadata_cid:
            return {"models": {}, "version": "1.0"}
        metadata_json = client.cat(self.metadata_cid)
        return json.loads(metadata_json)

    def _store_metadata(self, metadata):
        client = IPFSClient()
        metadata_json = json.dumps(metadata)
        result = client.add_json(metadata_json)
        self.metadata_cid = self.extract_hash(result)

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
        client = IPFSClient()
        model_cid = client.add_bytes(serialized_model)['Hash']
        manifest = {
            "model_id": model_id,
            "version": version,
            "model_hash": model_cid
        }
        manifest_cid = self.extract_hash(client.add_json(json.dumps(manifest)))
        
        metadata = self._get_metadata()
        if model_id not in metadata['models']:
            metadata['models'][model_id] = {}
        metadata['models'][model_id][version] = manifest_cid
        self._store_metadata(metadata)
        
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