import json
import logging
from core.ipfs_client import IPFSClient
from packaging import version as parse
from datetime import datetime

def get_metadata():
    client = IPFSClient()
    try:
        objects = client.list_objects()
        metadata = {"models": {}, "version": "1.0"}

        for obj in objects:
            try:
                content = client.cat(obj['Hash'])
                data = json.loads(content)
                if isinstance(data, dict) and 'model_id' in data and 'version' in data:
                    model_id = data['model_id']
                    version = data['version']
                    if model_id not in metadata['models']:
                        metadata['models'][model_id] = {'versions': {}, 'latest_version': version}
                    metadata['models'][model_id]['versions'][version] = obj['Hash']
                    if version > metadata['models'][model_id]['latest_version']:
                        metadata['models'][model_id]['latest_version'] = version
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logging.error(f"Error processing object {obj['Hash']}: {str(e)}")

        logging.info(f"Retrieved metadata: {metadata}")
        return metadata
    except Exception as e:
        logging.error(f"Error retrieving metadata: {str(e)}")
        raise

def store_metadata(metadata):
    client = IPFSClient()
    try:
        new_cid = client.add_json(metadata)
        logging.info(f"Stored metadata with new CID: {new_cid}")
        return new_cid
    except Exception as e:
        logging.error(f"Error storing metadata: {str(e)}")
        raise

def get_manifest_cid(model_id: str, version: str) -> str:
    metadata = get_metadata()
    if model_id not in metadata['models'] or version not in metadata['models'][model_id]['versions']:
        raise ValueError(f"No manifest CID found for {model_id} v{version}")
    return metadata['models'][model_id]['versions'][version]

def get_all_latest_models():
    metadata = get_metadata()
    latest_models = {}
    for model_id, versions in metadata['models'].items():
        if versions:
            latest_version = versions['latest_version']
            latest_models[model_id] = {
                'version': latest_version,
                'cid': versions['versions'][latest_version]
            }
    return latest_models