import logging
from core.ipfs_client import IPFSClient
from .metadata import get_manifest_cid

def download_model(model_id: str, version: str) -> bytes:
    client = IPFSClient()
    try:
        manifest_cid = get_manifest_cid(model_id, version)
        manifest = client.get_json(manifest_cid)
        if not manifest or 'model_cid' not in manifest:
            raise ValueError(f"Invalid manifest for {model_id} v{version}")
        
        model_cid = manifest['model_cid']
        model_data = client.cat(model_cid)
        if not model_data:
            raise ValueError(f"Failed to retrieve model data for {model_id} v{version}")
        
        return model_data
    except Exception as e:
        logging.error(f"Error in download_model: {str(e)}", exc_info=True)
        raise