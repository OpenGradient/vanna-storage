import logging
from core.ipfs_client import IPFSClient
from .metadata import get_metadata, store_metadata

def upload_model(model_id: str, serialized_model: bytes, version: str) -> str:
    client = IPFSClient()
    try:
        model_cid = client.add_bytes(serialized_model)
        logging.debug(f"Uploaded model with CID: {model_cid}")
        manifest = {
            "model_id": model_id,
            "version": version,
            "model_cid": model_cid
        }
        manifest_cid = client.add_json(manifest)
        logging.debug(f"Stored manifest with CID: {manifest_cid}")

        metadata = get_metadata()
        if 'models' not in metadata:
            metadata['models'] = {}
        if model_id not in metadata['models']:
            metadata['models'][model_id] = {}
        metadata['models'][model_id][version] = manifest_cid
        store_metadata(metadata)

        return manifest_cid
    except Exception as e:
        logging.error(f"Error in upload_model: {str(e)}", exc_info=True)
        raise