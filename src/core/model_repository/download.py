import logging
from core.ipfs_client import IPFSClient
from .metadata import get_manifest_cid

def download_model(model_id: str, version: str) -> bytes:
    client = IPFSClient()
    try:
        manifest_cid = get_manifest_cid(model_id, version)
        logging.info(f"Retrieved manifest CID: {manifest_cid} for {model_id} v{version}")
        
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
        
        logging.info(f"Retrieved model CID: {model_cid}")
        
        model_data = client.cat(model_cid)
        if not model_data:
            raise ValueError(f"Failed to retrieve model data for {model_id} v{version}")
        
        logging.info(f"Successfully retrieved model data, size: {len(model_data)} bytes")
        return model_data
    except Exception as e:
        logging.error(f"Error in download_model: {str(e)}", exc_info=True)
        raise