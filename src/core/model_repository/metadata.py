import json
from .base import ModelRepository
from core.ipfs_client import IPFSClient
import logging

def initialize_metadata(self):
    client = IPFSClient()
    initial_metadata = {"models": {}, "version": "1.0"}
    self.metadata_cid = self._store_metadata(initial_metadata)
    logging.info(f"Initialized new metadata with CID: {self.metadata_cid}")
    return initial_metadata

def _get_metadata(self):
    client = IPFSClient()
    try:
        if not self.metadata_cid:
            logging.warning("No metadata CID found. Initializing new metadata.")
            return self.initialize_metadata()

        metadata_json = client.cat(self.metadata_cid)
        if isinstance(metadata_json, bytes):
            metadata_json = metadata_json.decode('utf-8')
        metadata = json.loads(metadata_json)
        logging.debug(f"Retrieved metadata: {metadata}")
        return metadata
    except Exception as e:
        logging.error(f"Error retrieving metadata: {str(e)}", exc_info=True)
        # Optionally, reinitialize metadata if retrieval fails
        return self.initialize_metadata()

def _store_metadata(self, metadata):
    client = IPFSClient()
    try:
        logging.info(f"Storing metadata (before IPFS): {metadata}")
        result = client.add_json(metadata)
        logging.info(f"IPFS add_json result: {result}")
        if isinstance(result, dict) and 'Hash' in result:
            new_cid = result['Hash']
            self.metadata_cid = new_cid
            logging.info(f"Stored metadata with new CID: {new_cid}")
            # Verify stored data
            stored_data = client.cat(new_cid)
            logging.info(f"Verification - Retrieved data: {stored_data}")
            return new_cid
        else:
            raise ValueError(f"Unexpected result from IPFS add_json: {result}")
    except Exception as e:
        logging.error(f"Error storing metadata: {str(e)}", exc_info=True)
        raise

def get_manifest_cid(self, model_id: str, version: str) -> str:
    metadata = self._get_metadata()
    return metadata.get('models', {}).get(model_id, {}).get(version)

def add_model_version(self, model_id: str, version: str, manifest_cid: str):
    metadata = self._get_metadata()
    if model_id not in metadata['models']:
        metadata['models'][model_id] = {}
    metadata['models'][model_id][version] = manifest_cid
    self._store_metadata(metadata)

def list_versions(self, model_id: str) -> list:
    metadata = self._get_metadata()
    return list(metadata.get('models', {}).get(model_id, {}).keys())

ModelRepository.initialize_metadata = initialize_metadata
ModelRepository._get_metadata = _get_metadata
ModelRepository._store_metadata = _store_metadata
ModelRepository.get_manifest_cid = get_manifest_cid
ModelRepository.add_model_version = add_model_version
ModelRepository.list_versions = list_versions