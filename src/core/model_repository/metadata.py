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
    if not self.metadata_cid:
        return {"models": {}, "version": "1.0"}
    metadata_json = client.cat(self.metadata_cid)
    try:
        if isinstance(metadata_json, bytes):
            metadata_json = metadata_json.decode('utf-8')
        metadata = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json
        if not isinstance(metadata, dict):
            raise TypeError(f"Decoded metadata is not a dict: {metadata}")
        return metadata
    except (json.JSONDecodeError, TypeError) as e:
        logging.error(f"Failed to decode metadata JSON: {metadata_json}. Error: {str(e)}")
        return {"models": {}, "version": "1.0"}

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

ModelRepository.initialize_metadata = initialize_metadata
ModelRepository._get_metadata = _get_metadata
ModelRepository._store_metadata = _store_metadata
ModelRepository.get_manifest_cid = get_manifest_cid