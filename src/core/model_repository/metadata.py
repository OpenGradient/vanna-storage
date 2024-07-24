import json
from .base import ModelRepository
from core.ipfs_client import IPFSClient
import logging

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
    logging.debug(f"Current metadata CID: {self.metadata_cid}")
    if not self.metadata_cid:
        logging.warning("No metadata CID found, returning default metadata")
        return {"models": {}, "version": "1.0"}
    try:
        metadata_json = client.cat(self.metadata_cid)
        logging.debug(f"Raw metadata from IPFS: {metadata_json}")
        
        if isinstance(metadata_json, bytes):
            metadata_json = metadata_json.decode('utf-8')
        logging.debug(f"Decoded metadata: {metadata_json}")
        
        metadata = json.loads(metadata_json)
        logging.debug(f"Parsed metadata: {metadata}")
        
        if not isinstance(metadata, dict):
            logging.error(f"Parsed metadata is not a dict: {metadata}")
            return {"models": {}, "version": "1.0"}
        
        return metadata
    except Exception as e:
        logging.error(f"Error retrieving metadata: {str(e)}", exc_info=True)
        return {"models": {}, "version": "1.0"}
    
def _store_metadata(self, metadata):
    client = IPFSClient()
    try:
        metadata_json = json.dumps(metadata)
        logging.debug(f"Storing metadata: {metadata_json}")
        result = client.add_json(metadata)  # Changed from metadata_json to metadata
        logging.debug(f"IPFS add_json result: {result}")
        if isinstance(result, dict) and 'Hash' in result:
            self.metadata_cid = result['Hash']
        else:
            raise ValueError(f"Unexpected result from IPFS add_json: {result}")
        logging.info(f"Stored metadata with CID: {self.metadata_cid}")
        return self.metadata_cid
    except Exception as e:
        logging.error(f"Error storing metadata: {str(e)}", exc_info=True)
        raise

def get_manifest_cid(self, model_id: str, version: str) -> str:
    metadata = self._get_metadata()
    if model_id in metadata.get('models', {}) and version in metadata['models'][model_id]:
        return metadata['models'][model_id][version]
    return None

ModelRepository.initialize_metadata = initialize_metadata
ModelRepository._get_metadata = _get_metadata
ModelRepository._store_metadata = _store_metadata
ModelRepository.get_manifest_cid = get_manifest_cid