import json
import logging
from core.ipfs_client import IPFSClient
from packaging import version as parse
from datetime import datetime
from typing import List
import re

def upload_model(model_id: str, serialized_model: bytes, version: str) -> str:
    client = IPFSClient()
    try:
        # Validate version format
        if not re.match(r'^\d+\.\d{2}$', version):
            raise ValueError(f"Invalid version format. Must be in the form 'x.yz' where x and y are integers.")

        metadata = get_metadata()
        
        # Version validation
        if model_id in metadata['models']:
            existing_versions = metadata['models'][model_id].get('versions', {}).keys()
            if not all(parse.parse(version) > parse.parse(v) for v in existing_versions):
                raise ValueError(f"Version {version} is not greater than all existing versions for model {model_id}")
        
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
            metadata['models'][model_id] = {'versions': {}, 'latest_version': '0.00'}
        metadata['models'][model_id]['versions'][version] = manifest_cid
        
        # Update latest version
        current_latest = metadata['models'][model_id]['latest_version']
        if parse.parse(version) > parse.parse(current_latest):
            metadata['models'][model_id]['latest_version'] = version

        store_metadata(metadata)
        return manifest_cid
    except Exception as e:
        logging.error(f"Error uploading model: {str(e)}")
        raise

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

def get_model_content(model_id: str, version: str) -> dict:
    try:
        manifest_cid = get_manifest_cid(model_id, version)
        
        client = IPFSClient()
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
        
        return {
            'manifest': manifest,
            'content': {
                'model': model_cid
            }
        }
    except Exception as e:
        logging.error(f"Error in get_model_content: {str(e)}", exc_info=True)
        raise

def list_versions(model_id: str) -> List[str]:
    metadata = get_metadata()
    return list(metadata.get('models', {}).get(model_id, {}).keys())

def get_latest_version(model_id: str) -> str:
    versions = list_versions(model_id)
    if not versions:
        raise ValueError(f"No versions available for model_id {model_id}")
    return max(versions, key=lambda v: parse.parse(v))

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
                        metadata['models'][model_id] = {'versions': {}, 'latest_version': '0.00'}
                    metadata['models'][model_id]['versions'][version] = obj['Hash']
                    if parse.parse(version) > parse.parse(metadata['models'][model_id]['latest_version']):
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

# Export all functions
__all__ = [
    'get_metadata', 'store_metadata', 'get_manifest_cid', 'get_all_latest_models',
    'upload_model', 'download_model',
    'list_versions', 'get_latest_version', 
]