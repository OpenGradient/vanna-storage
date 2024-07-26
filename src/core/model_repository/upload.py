import logging
from core.ipfs_client import IPFSClient
from .metadata import get_metadata
from datetime import datetime

def upload_model(model_id: str, serialized_model: bytes, version: str) -> str:
    client = IPFSClient()
    try:
        metadata = get_metadata()
        if model_id in metadata['models'] and version in metadata['models'][model_id]:
            raise ValueError(f"Version {version} already exists for model {model_id}")

        model_cid = client.add_bytes(serialized_model)
        logging.debug(f"Uploaded model with CID: {model_cid}")
        manifest = {
            "model_id": model_id,
            "version": version,
            "model_cid": model_cid,
            "created_at": datetime.now().isoformat()
        }
        manifest_cid = client.add_json(manifest)
        logging.debug(f"Stored manifest with CID: {manifest_cid}")

        # Update metadata
        if model_id not in metadata['models']:
            metadata['models'][model_id] = {}
        metadata['models'][model_id][version] = manifest_cid
        
        # Update latest version
        if 'latest_version' not in metadata['models'][model_id] or version > metadata['models'][model_id]['latest_version']:
            metadata['models'][model_id]['latest_version'] = version

        # Store updated metadata
        new_metadata_cid = client.add_json(metadata)
        logging.debug(f"Updated metadata stored with CID: {new_metadata_cid}")

        return manifest_cid
    except Exception as e:
        logging.error(f"Error in upload_model: {str(e)}", exc_info=True)
        raise