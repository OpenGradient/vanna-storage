import json
from .base import ModelRepository
from core.ipfs_client import IPFSClient
import logging
import traceback

def _get_metadata(self):
    client = IPFSClient()
    try:
        if not self.metadata_cid:
            logging.error("No metadata CID found. Initializing empty metadata.")
            return {"models": {}, "version": "1.0"}

        logging.info(f"Retrieving metadata with CID: {self.metadata_cid}")
        metadata_json = client.cat(self.metadata_cid)
        if not metadata_json:
            logging.error(f"Failed to retrieve metadata for CID: {self.metadata_cid}")
            return {"models": {}, "version": "1.0"}
        if isinstance(metadata_json, bytes):
            metadata_json = metadata_json.decode('utf-8')
        metadata = json.loads(metadata_json)
        logging.info(f"Retrieved metadata: {metadata}")
        if not isinstance(metadata, dict) or 'models' not in metadata:
            logging.error(f"Invalid metadata structure: {metadata}")
            return {"models": {}, "version": "1.0"}
        return metadata
    except Exception as e:
        logging.error(f"Error retrieving metadata: {str(e)}", exc_info=True)
        return {"models": {}, "version": "1.0"}

def _store_metadata(self, metadata):
    client = IPFSClient()
    try:
        logging.info(f"Storing metadata: {metadata}")
        result = client.add_json(metadata)
        logging.info(f"IPFS add_json result: {result}")
        if isinstance(result, dict) and 'Hash' in result:
            new_cid = result['Hash']
            self.metadata_cid = new_cid
            logging.info(f"Stored metadata with new CID: {new_cid}")
            # Verify stored data
            stored_data = self._get_metadata()
            logging.info(f"Verification - Retrieved data: {stored_data}")
            if stored_data != metadata:
                logging.error(f"Stored metadata does not match original. Original: {metadata}, Stored: {stored_data}")
            return new_cid
        else:
            raise ValueError(f"Unexpected result from IPFS add_json: {result}")
    except Exception as e:
        logging.error(f"Error storing metadata: {str(e)}", exc_info=True)
        raise

def get_manifest_cid(self, model_id: str, version: str) -> str:
    try:
        metadata = self._get_metadata()
        logging.debug(f"Metadata retrieved in get_manifest_cid: {metadata}")
        if 'models' not in metadata or model_id not in metadata['models'] or version not in metadata['models'][model_id]:
            raise ValueError(f"No manifest CID found for {model_id} v{version}")
        manifest_cid = metadata['models'][model_id][version]
        logging.debug(f"Manifest CID for {model_id} v{version}: {manifest_cid}")
        return manifest_cid
    except Exception as e:
        logging.error(f"Error in get_manifest_cid: {str(e)}")
        logging.error(traceback.format_exc())
        raise ValueError(f"Failed to get manifest CID: {str(e)}")

def add_model_version(self, model_id: str, version: str, manifest_cid: str):
    metadata = self._get_metadata()
    if model_id not in metadata['models']:
        metadata['models'][model_id] = {}
    metadata['models'][model_id][version] = manifest_cid
    self._store_metadata(metadata)

def list_versions(self, model_id: str) -> list:
    metadata = self._get_metadata()
    return list(metadata.get('models', {}).get(model_id, {}).keys())

ModelRepository._get_metadata = _get_metadata
ModelRepository._store_metadata = _store_metadata
ModelRepository.get_manifest_cid = get_manifest_cid
ModelRepository.add_model_version = add_model_version
ModelRepository.list_versions = list_versions