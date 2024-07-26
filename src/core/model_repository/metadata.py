import json
import time
from .base import ModelRepository
from core.ipfs_client import IPFSClient
import logging
import traceback
from packaging import version as parse

def _get_metadata(self):
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
                        metadata['models'][model_id] = {}
                    metadata['models'][model_id][version] = obj['Hash']
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logging.error(f"Error processing object {obj['Hash']}: {str(e)}")

        logging.info(f"Retrieved metadata: {metadata}")
        return metadata
    except Exception as e:
        logging.error(f"Error retrieving metadata: {str(e)}")
        return {"models": {}, "version": "1.0"}

def _store_metadata(self, metadata):
    client = IPFSClient()
    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"Attempting to store metadata (attempt {attempt + 1}): {metadata}")
            new_cid = client.add_json(metadata)
            print(f"Stored metadata with new CID: {new_cid}")
            self.metadata_cid = new_cid

            # Verify stored data
            stored_data = client.get_json(new_cid)
            if stored_data == metadata:
                print("Metadata verification successful")
                return new_cid
            else:
                print(f"Stored metadata does not match original. Original: {metadata}, Stored: {stored_data}")
        except Exception as e:
            print(f"Error storing metadata (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(1)  # Wait for 1 second before retrying

def get_manifest_cid(self, model_id: str, version: str) -> str:
    try:
        metadata = self._get_metadata()
        print(f"Metadata retrieved in get_manifest_cid: {metadata}")
        if 'models' not in metadata or model_id not in metadata['models'] or version not in metadata['models'][model_id]:
            raise ValueError(f"No manifest CID found for {model_id} v{version}")
        manifest_cid = metadata['models'][model_id][version]
        print(f"Manifest CID for {model_id} v{version}: {manifest_cid}")
        return manifest_cid
    except Exception as e:
        print(f"Error in get_manifest_cid: {str(e)}")
        print(traceback.format_exc())
        raise ValueError(f"Failed to get manifest CID: {str(e)}")

def add_model_version(self, model_id: str, version: str, manifest_cid: str):
    metadata = self._get_metadata()
    if model_id not in metadata['models']:
        metadata['models'][model_id] = {}
    metadata['models'][model_id][version] = manifest_cid
    self._store_metadata(metadata)

def list_versions(self, model_id: str) -> list:
    metadata = self._get_metadata()
    versions = list(metadata.get('models', {}).get(model_id, {}).keys())
    return [v for v in versions if v != 'latest']

def get_all_latest_models(self):
    metadata = self._get_metadata()
    latest_models = {}
    for model_id, versions in metadata['models'].items():
        if versions:
            latest_version = max(versions.keys(), key=lambda v: parse(v))
            latest_models[model_id] = {
                'version': latest_version,
                'cid': versions[latest_version]
            }
    return latest_models

ModelRepository.get_all_latest_models = get_all_latest_models
ModelRepository._get_metadata = _get_metadata
ModelRepository._store_metadata = _store_metadata
ModelRepository.get_manifest_cid = get_manifest_cid
ModelRepository.add_model_version = add_model_version
ModelRepository.list_versions = list_versions