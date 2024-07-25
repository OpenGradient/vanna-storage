import logging
import traceback
from .base import ModelRepository
from core.ipfs_client import IPFSClient

def download_model(self, model_id: str, version: str) -> bytes:
    client = IPFSClient()
    try:
        logging.info(f"Starting download for model: {model_id}, version: {version}")
        
        # Get metadata
        metadata = self._get_metadata()
        logging.info(f"Retrieved metadata: {metadata}")
        
        if 'models' not in metadata or model_id not in metadata['models'] or version not in metadata['models'][model_id]:
            raise ValueError(f"No manifest found for model {model_id} version {version}")
        
        manifest_cid = metadata['models'][model_id][version]
        logging.info(f"Manifest CID for {model_id} v{version}: {manifest_cid}")
        
        manifest = client.get_json(manifest_cid)
        if not manifest:
            raise ValueError(f"Failed to retrieve manifest for {model_id} v{version}")
        logging.info(f"Retrieved manifest: {manifest}") 
        
        if not isinstance(manifest, dict) or 'model_cid' not in manifest:
            raise ValueError(f"Invalid manifest structure for {model_id} v{version}")
        
        model_cid = manifest['model_cid']
        logging.info(f"Model CID from manifest: {model_cid}")
        
        logging.info(f"Attempting to retrieve model data with CID: {model_cid}")
        model_data = client.cat(model_cid)
        if not model_data:
            raise ValueError(f"Failed to retrieve model data for {model_id} v{version}")
        logging.info(f"Retrieved model data, size: {len(model_data)} bytes")
        
        return model_data
    except Exception as e:
        logging.error(f"Error in download_model: {str(e)}")
        logging.error(traceback.format_exc())
        raise

ModelRepository.download_model = download_model