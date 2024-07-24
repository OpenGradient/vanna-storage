import json
import logging
from .base import ModelRepository
from core.ipfs_client import IPFSClient

def upload_model(self, model_id: str, serialized_model: bytes, version: str) -> str:
    client = IPFSClient()
    try:
        model_cid = client.add_bytes(serialized_model)['Hash']
        manifest = {
            "model_id": model_id,
            "version": version,
            "model_hash": model_cid
        }
        manifest_cid = self.extract_hash(client.add_json(json.dumps(manifest)))
        
        metadata = self._get_metadata()
        logging.debug(f"Retrieved metadata type: {type(metadata)}")
        logging.debug(f"Retrieved metadata content: {metadata}")
        
        if not isinstance(metadata, dict):
            logging.error(f"Metadata is not a dict. Type: {type(metadata)}, Content: {metadata}")
            raise TypeError(f"Expected metadata to be a dict, but got {type(metadata)}")
        
        if 'models' not in metadata:
            metadata['models'] = {}
        if model_id not in metadata['models']:
            metadata['models'][model_id] = {}
        metadata['models'][model_id][version] = manifest_cid
        self._store_metadata(metadata)
        
        logging.info(f"Successfully uploaded model {model_id} version {version}")
        return manifest_cid
    except Exception as e:
        logging.error(f"Error in upload_model: {str(e)}", exc_info=True)
        raise

ModelRepository.upload_model = upload_model