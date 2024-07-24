from .base import ModelRepository
from core.ipfs_client import IPFSClient
import json
import logging

def get_model_content(self, model_id: str, version: str) -> dict:
    client = IPFSClient()
    try:
        manifest_cid = self.get_manifest_cid(model_id, version)
        logging.debug(f"Retrieved manifest CID: {manifest_cid}")
        if not manifest_cid:
            raise ValueError(f"No manifest found for model {model_id} version {version}")
        
        manifest_data = client.cat(manifest_cid)
        logging.debug(f"Raw manifest data: {manifest_data}")
        
        if isinstance(manifest_data, bytes):
            manifest_data = manifest_data.decode('utf-8')
        logging.debug(f"Decoded manifest data: {manifest_data}")
        
        try:
            manifest = json.loads(manifest_data)
            logging.debug(f"Parsed manifest: {manifest}")
        except json.JSONDecodeError:
            logging.error(f"Failed to parse manifest JSON: {manifest_data}")
            raise ValueError(f"Invalid manifest format for model {model_id} version {version}")
        
        if isinstance(manifest, dict) and 'Message' in manifest:
            raise ValueError(f"Error retrieving manifest: {manifest['Message']}")
        
        if not isinstance(manifest, dict):
            logging.error(f"Manifest is not a dictionary: {type(manifest)}")
            raise ValueError(f"Invalid manifest format for model {model_id} version {version}")
        
        model_hash = manifest.get('model_hash')
        if not model_hash:
            logging.error(f"No model hash found in manifest: {manifest}")
            raise ValueError(f"No model hash found in manifest for model {model_id} version {version}")
        
        logging.debug(f"Retrieved model hash: {model_hash}")
        model_data = client.cat(model_hash)
        logging.debug(f"Retrieved model data, size: {len(model_data)} bytes")
        
        try:
            model_content = json.loads(model_data)
            logging.debug("Model data parsed as JSON")
        except json.JSONDecodeError:
            import base64
            model_content = base64.b64encode(model_data).decode('utf-8')
            logging.debug("Model data encoded as base64")
        
        return {
            "model_id": model_id,
            "version": version,
            "manifest": manifest,
            "content": model_content
        }
    except Exception as e:
        logging.error(f"Error in get_model_content: {str(e)}", exc_info=True)
        raise
    
ModelRepository.get_model_content = get_model_content