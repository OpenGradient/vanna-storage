from .base import ModelRepository
from core.ipfs_client import IPFSClient
import logging
import traceback

def download_model(self, model_id: str, version: str) -> bytes:
    client = IPFSClient()
    try:
        logging.debug(f"Attempting to download model: {model_id}, version: {version}")
        manifest_cid = self.get_manifest_cid(model_id, version)
        logging.debug(f"Manifest CID for {model_id} v{version}: {manifest_cid}")
        if not manifest_cid:
            raise ValueError(f"No manifest found for model {model_id} version {version}")
        
        manifest = client.get_json(manifest_cid)
        logging.debug(f"Retrieved manifest: {manifest}") 
        
        if 'model_cid' not in manifest:
            logging.error(f"Manifest does not contain 'model_cid'. Manifest keys: {manifest.keys()}")
            raise ValueError(f"Invalid manifest structure for {model_id} v{version}")
        
        model_cid = manifest['model_cid']
        logging.debug(f"Model CID from manifest: {model_cid}")
        
        logging.debug(f"Attempting to retrieve model data with CID: {model_cid}")
        model_data = client.cat(model_cid)
        logging.debug(f"Retrieved model data, size: {len(model_data)} bytes")
        return model_data
    except Exception as e:
        logging.error(f"Error in download_model: {str(e)}")
        logging.error(f"Manifest content: {manifest}")
        logging.error(traceback.format_exc())
        raise

ModelRepository.download_model = download_model