from core.ipfs_client import IPFSClient
from .metadata import get_manifest_cid
import logging

def get_model_content(model_id: str, version: str) -> dict:
    try:
        manifest_cid = get_manifest_cid(model_id, version)
        
        client = IPFSClient()
        manifest = client.get_json(manifest_cid)
        if not manifest or 'model_cid' not in manifest:
            raise ValueError(f"Invalid manifest structure for {model_id} v{version}")
        
        model_cid = manifest['model_cid']
        
        return {
            'manifest': manifest,
            'content': {
                'model': model_cid
            }
        }
    except Exception as e:
        logging.error(f"Error in get_model_content: {str(e)}", exc_info=True)
        raise