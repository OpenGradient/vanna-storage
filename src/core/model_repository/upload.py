import logging
from .base import ModelRepository
from core.ipfs_client import IPFSClient
import json

def upload_model(self, model_id: str, serialized_model: bytes, version: str) -> str:
    client = IPFSClient()
    try:
        model_cid = client.add_bytes(serialized_model)['Hash']
        logging.debug(f"Uploaded model with CID: {model_cid}")
        manifest = {
            "model_id": model_id,
            "version": version,
            "model_cid": model_cid
        }
        logging.debug(f"Created manifest: {manifest}")
        manifest_cid = client.add_json(manifest)['Hash']
        logging.debug(f"Stored manifest with CID: {manifest_cid}")

        # Retrieve existing metadata
        metadata = self._get_metadata()
        logging.debug(f"Current metadata before update: {metadata}")

        # Ensure models key exists
        if 'models' not in metadata:
            metadata['models'] = {}

        # Ensure the model_id key exists
        if model_id not in metadata['models']:
            metadata['models'][model_id] = {}

        # Update the version with the new manifest CID
        metadata['models'][model_id][version] = manifest_cid
        logging.debug(f"Updated metadata: {metadata}")

        # Store the updated metadata
        new_metadata_cid = self._store_metadata(metadata)
        logging.debug(f"New metadata stored with CID: {new_metadata_cid}")
        self.metadata_cid = new_metadata_cid  # Update the instance variable

        # Verify the metadata was updated correctly
        updated_metadata = self._get_metadata()
        logging.debug(f"Verified updated metadata: {updated_metadata}")

        return manifest_cid
    except Exception as e:
        logging.error(f"Error in upload_model: {str(e)}", exc_info=True)
        raise

ModelRepository.upload_model = upload_model