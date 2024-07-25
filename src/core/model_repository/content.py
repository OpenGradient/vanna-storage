from .base import ModelRepository
from core.ipfs_client import IPFSClient
import json
import logging
import base64

def get_model_content(self, model_id: str, version: str) -> dict:
    manifest_cid = self.get_manifest_cid(model_id, version)
    if not manifest_cid:
        raise ValueError(f"No manifest found for model {model_id} version {version}")
    
    client = IPFSClient()
    try:
        manifest = client.get_json(manifest_cid)
        logging.debug(f"Retrieved manifest: {manifest}")
        
        if not isinstance(manifest, dict):
            raise ValueError(f"Invalid manifest format for model {model_id} version {version}")
        
        model_content = client.cat(manifest.get("model_cid", ""))
        
        return {
            "model_id": model_id,
            "version": version,
            "manifest": manifest,
            "content": {
                "model": base64.b64encode(model_content).decode('utf-8'),
            }
        }
    except Exception as e:
        logging.error(f"Error retrieving model content: {str(e)}", exc_info=True)
        raise

ModelRepository.get_model_content = get_model_content