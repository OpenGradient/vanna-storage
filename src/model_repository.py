import json
import os
import time
from typing import Dict, List
from ipfs_client import ipfs_client
from packaging.version import parse  # Import the parse function here

# Assuming the existence of a config.py for storing configurations
from model_config import MODEL_FOLDER
from functools import wraps

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

    def __init__(self):
        self.metadata_cid = None
        self.initialize_metadata()

    @rate_limit(0)  # Limit to once every 5 minutes (set back to 300)
    def initialize_metadata(self, force=False):
        """
        Initializes or resets the metadata for the ModelRepository with added safeguards.

        This method creates a new, empty metadata structure and stores it in IPFS.
        It includes safeguards such as confirmation, backup, printing, and rate limiting.

        Args:
            force (bool): If True, bypasses the confirmation prompt. Use with caution.

        Returns:
            str: The CID (Content Identifier) of the newly initialized metadata in IPFS.

        Raises:
            ValueError: If the operation is cancelled by the user or rate limit is exceeded.
            ipfshttpclient.exceptions.Error: If there's an error communicating with the IPFS daemon.
            json.JSONEncodeError: If there's an error encoding the empty dictionary to JSON.

        Example:
            >>> repo = ModelRepository()
            >>> metadata_cid = repo.initialize_metadata()
            >>> print(f"New metadata CID: {metadata_cid}")
            New metadata CID: QmX1Y2Z3...

        Note:
            This method should be used with caution as it will overwrite any existing
            metadata. It's primarily intended for initial setup or in scenarios where
            a complete reset of the metadata is desired.
        """
        if not force:
            confirmation = input("Warning: This will reset all metadata. Are you sure? (yes/no): ")
            if confirmation.lower() != 'yes':
                print("Metadata initialization cancelled by user.")
                raise ValueError("Operation cancelled by user.")

        print("Initializing metadata...")

        try:
            # Backup existing metadata if it exists
            if self.metadata_cid:
                with ipfs_client() as client:
                    existing_metadata = client.cat(self.metadata_cid)
                    backup_cid = client.add_bytes(existing_metadata)
                    print(f"Backup of existing metadata created with CID: {backup_cid}")

            # Initialize new metadata
            new_metadata = {}
            with ipfs_client() as client:
                result = client.add_json(json.dumps(new_metadata))
                new_metadata_cid = self.extract_hash(result)

            self.metadata_cid = new_metadata_cid
            print(f"Metadata initialized successfully. New CID: {new_metadata_cid}")
            return new_metadata_cid

        except Exception as e:
            print(f"Error during metadata initialization: {str(e)}")
            raise
    
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
        with ipfs_client() as client:
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
        """
        Retrieves the manifest CID for a specific model and version from the metadata stored in IPFS.

        This method fetches the metadata from IPFS, parses it, and returns the manifest CID
        for the specified model and version. It includes error handling for various scenarios
        such as missing metadata, invalid JSON, and missing model or version information.

        Args:
            model_id (str): The unique identifier for the model.
            version (str): The version of the model.

        Returns:
            str: The manifest CID for the specified model and version.

        Raises:
            ValueError: If the metadata is not stored, cannot be parsed, or if the specified
                        model and version combination is not found in the metadata.

        Example:
            >>> repo = ModelRepository()
            >>> manifest_cid = repo.get_manifest_cid("model_123", "1.0")
            >>> print(manifest_cid)
            'QmA1b2C3d4E5f6G7h8I9j0K1L2m3N4o5P6q7R8s9T0u1V2w3X4y5Z'
        """
        if not self.metadata_cid:
            raise ValueError("No metadata stored yet")

        print(f"Retrieving metadata with CID: {self.metadata_cid}")
        with ipfs_client() as client:
            try:
                metadata_json = client.cat(self.metadata_cid)
                print(f"Raw metadata: {metadata_json}")
                metadata = json.loads(metadata_json)
                print(f"Retrieved metadata: {metadata}")
                print(f"Metadata type: {type(metadata)}")
                
                if isinstance(metadata, str):
                    print("Metadata is a string, attempting to parse as JSON")
                    metadata = json.loads(metadata)
                    print(f"Parsed metadata: {metadata}")
                
                if not isinstance(metadata, dict):
                    print(f"Warning: Metadata is not a dictionary. Unable to process.")
                    raise ValueError("Invalid metadata format")
                
                print(f"Metadata after type check: {metadata}")
                
                if model_id not in metadata:
                    print(f"Model ID {model_id} not found in metadata")
                    raise ValueError(f"No manifest found for model {model_id}")
                
                if version not in metadata[model_id]:
                    print(f"Version {version} not found for model {model_id}")
                    raise ValueError(f"No manifest found for model {model_id} version {version}")
                
                manifest_cid = metadata[model_id][version]
                print(f"Found manifest CID: {manifest_cid}")
                return manifest_cid
                
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error parsing metadata: {str(e)}")
                raise ValueError(f"Error parsing metadata: {str(e)}")
            
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
    def upload_model(self, model_id: str, serialized_model: bytes, version: str, file_path: str = None) -> str:
        with ipfs_client() as client:
            model_hash = self.extract_hash(client.add_bytes(serialized_model))
            
            files = {}
            if file_path:
                file_result = client.add(file_path)
                file_hash = self.extract_hash(file_result)
                files[os.path.basename(file_path)] = file_hash

            manifest = {
                "model_id": model_id,
                "version": version,
                "files": files,
                "model_hash": model_hash
            }
            manifest_json = json.dumps(manifest)
            manifest_cid = self.extract_hash(client.add_json(manifest))
            self._store_manifest_cid(model_id, version, manifest_cid)

            return manifest_cid

    def download_model(self, model_id: str, version: str) -> bytes:
        with ipfs_client() as client:
            # Retrieve the manifest for the specified version
            manifest_cid = self.get_manifest_cid(model_id, version)
            if not manifest_cid:
                raise ValueError(f"No manifest found for model {model_id} version {version}")
            
            # Get the manifest content
            manifest = client.cat(manifest_cid)
            manifest_data = json.loads(manifest)
            
            # Get the model hash from the manifest
            model_hash = manifest_data['model_hash']
            
            # Download and return the model data
            model_data = client.cat(model_hash)
            return model_data
 
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
            return True
        return all(parse(new_version) > parse(v) for v in existing_versions)

    def list_versions(self, model_id: str) -> List[str]:
        """
        Lists all available versions for a given model_id.
        """
        if not self.metadata_cid:
            return []
        
        with ipfs_client() as client:
            metadata_json = client.cat(self.metadata_cid)
            metadata = json.loads(metadata_json)
            
            if model_id in metadata:
                versions = list(metadata[model_id].keys())
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
    
    def validate_version(self, model_id: str, new_version: str) -> bool:
        """
        Validates the new version against existing versions to ensure it follows the versioning scheme.
        """
        existing_versions = self.list_versions(model_id)
        if not existing_versions:
            return True
        return all(parse(new_version) > parse(v) for v in existing_versions)

    def list_versions(self, model_id: str) -> List[str]:
        """
        Lists all available versions for a given model_id.
        """
        # Assuming MODEL_FOLDER is defined and points to the location where models are stored
        if not self.metadata_cid:
            return []
        
        with ipfs_client() as client:
            metadata_json = client.cat(self.metadata_cid)
            metadata = json.loads(metadata_json)
            
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            if model_id in metadata:
                versions = list(metadata[model_id].keys())
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