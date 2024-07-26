from core.ipfs_client import IPFSClient
from .metadata import get_manifest_cid
import logging

def get_model_content(model_id: str, version: str) -> dict:
    try:
        manifest_cid = get_manifest_cid(model_id, version)
        
        client = IPFSClient()
        manifest = client.get_json(manifest_cid)
        logging.info(f"Retrieved manifest: {manifest}")
        
        if not manifest:
            raise ValueError(f"Empty manifest for {model_id} v{version}")
        
        logging.info(f"Manifest keys: {manifest.keys()}")
        
        if 'model_cid' in manifest:
            model_cid = manifest['model_cid']
        elif 'model_hash' in manifest:
            model_cid = manifest['model_hash']
        else:
            raise ValueError(f"Invalid manifest structure for {model_id} v{version}. Neither 'model_cid' nor 'model_hash' found in {manifest}")
        
        return {
            'manifest': manifest,
            'content': {
                'model': model_cid
            }
        }
    except Exception as e:
        logging.error(f"Error in get_model_content: {str(e)}", exc_info=True)
        raise