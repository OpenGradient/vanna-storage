import logging
from .base import ModelRepository
from core.ipfs_client import IPFSClient

def upload_model(self, model_id: str, serialized_model: bytes, version: str) -> str:
    client = IPFSClient()
    try:
        model_cid = client.add_bytes(serialized_model)['Hash']
        logging.debug(f"Uploaded model with CID: {model_cid}")
        manifest = {
            "model_id": model_id,
            "version": version,
            "model_hash": model_cid
        }
        logging.debug(f"Created manifest: {manifest}")
        manifest_result = client.add_json(manifest)
        logging.debug(f"Raw manifest result: {manifest_result}")
        
        if isinstance(manifest_result, dict) and 'Hash' in manifest_result:
            manifest_cid = manifest_result['Hash']
        else:
            raise ValueError(f"Unexpected manifest result: {manifest_result}")
        
        logging.debug(f"Stored manifest with CID: {manifest_cid}")
        
        metadata = self._get_metadata()
        logging.debug(f"Current metadata before update: {metadata}")
        if 'models' not in metadata:
            metadata['models'] = {}
        if model_id not in metadata['models']:
            metadata['models'][model_id] = {}
        metadata['models'][model_id][version] = manifest_cid
        logging.debug(f"Updated metadata: {metadata}")
        
        new_metadata_cid = self._store_metadata(metadata)
        logging.debug(f"New metadata stored with CID: {new_metadata_cid}")
        
        # Verify the metadata was updated correctly
        updated_metadata = self._get_metadata()
        logging.debug(f"Verified updated metadata: {updated_metadata}")
        
        return manifest_cid
    except Exception as e:
        logging.error(f"Error in upload_model: {str(e)}", exc_info=True)
        raise
    
ModelRepository.upload_model = upload_model