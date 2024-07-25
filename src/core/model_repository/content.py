from .base import ModelRepository
from core.ipfs_client import IPFSClient
import logging
import traceback

def get_model_content(self, model_id: str, version: str) -> dict:
    try:
        metadata = self._get_metadata()
        logging.debug(f"Retrieved metadata in get_model_content: {metadata}")
        
        if 'models' not in metadata or model_id not in metadata['models'] or version not in metadata['models'][model_id]:
            raise ValueError(f"No manifest found for model {model_id} version {version}")
        
        manifest_cid = metadata['models'][model_id][version]
        logging.debug(f"Manifest CID for {model_id} v{version}: {manifest_cid}")
        
        client = IPFSClient()
        manifest = client.get_json(manifest_cid)
        if not manifest:
            raise ValueError(f"Failed to retrieve manifest for {model_id} v{version}")
        logging.debug(f"Retrieved manifest: {manifest}")
        
        if 'model_cid' not in manifest:
            raise ValueError(f"Invalid manifest structure for {model_id} v{version}")
        
        model_cid = manifest['model_cid']
        logging.debug(f"Model CID from manifest: {model_cid}")
        
        # We're not actually retrieving the model content here, just returning the CID
        return {
            'manifest': manifest,
            'content': {
                'model': model_cid
            }
        }
    except Exception as e:
        logging.error(f"Error in get_model_content: {str(e)}")
        logging.error(traceback.format_exc())
        raise

ModelRepository.get_model_content = get_model_content