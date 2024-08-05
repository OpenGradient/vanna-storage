import json
import logging
from core.ipfs_client import IPFSClient
from packaging import version as parse
from datetime import datetime
from typing import List
import re

class ModelRepository:
    def __init__(self):
        self.client = IPFSClient()

    def upload_model(self, model_id: str, serialized_model: bytes) -> str:
        try:
            metadata = self.get_metadata()
            
            # Get the current highest version or start at 1.00 if no versions exist
            if model_id in metadata['models']:
                current_versions = metadata['models'][model_id].get('versions', {}).keys()
                highest_version = max(current_versions, key=lambda v: parse.parse(v)) if current_versions else "0.99"
            else:
                highest_version = "0.99"
            
            # Increment the version
            major, minor = map(int, highest_version.split('.'))
            if minor == 99:
                new_version = f"{major + 1}.00"
            else:
                new_version = f"{major}.{minor + 1:02d}"
            
            model_cid = self.client.add_bytes(serialized_model)
            logging.debug(f"Uploaded model with CID: {model_cid}")
            manifest = {
                "model_id": model_id,
                "version": new_version,
                "model_cid": model_cid,
                "created_at": datetime.now().isoformat()
            }
            manifest_cid = self.client.add_json(manifest)
            logging.debug(f"Stored manifest with CID: {manifest_cid}")

            # Update metadata
            if model_id not in metadata['models']:
                metadata['models'][model_id] = {'versions': {}, 'latest_version': '0.00'}
            metadata['models'][model_id]['versions'][new_version] = manifest_cid
            metadata['models'][model_id]['latest_version'] = new_version

            self.store_metadata(metadata)
            return manifest_cid, new_version
        except Exception as e:
            logging.error(f"Error uploading model: {str(e)}")
            raise

    def download_model(self, model_id: str, version: str) -> bytes:
        try:
            manifest_cid = self.get_manifest_cid(model_id, version)
            logging.info(f"Retrieved manifest CID: {manifest_cid} for {model_id} v{version}")
            
            manifest = self.client.get_json(manifest_cid)
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
            
            model_data = self.client.cat(model_cid)
            if not model_data:
                raise ValueError(f"Failed to retrieve model data for {model_id} v{version}")
            
            logging.info(f"Successfully retrieved model data, size: {len(model_data)} bytes")
            return model_data
        except Exception as e:
            logging.error(f"Error in download_model: {str(e)}", exc_info=True)
            raise

    def get_model_content(self, model_id: str, version: str) -> dict:
        try:
            manifest_cid = self.get_manifest_cid(model_id, version)
            
            manifest = self.client.get_json(manifest_cid)
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

    def list_versions(self, model_id: str) -> List[str]:
        metadata = self.get_metadata()
        return list(metadata.get('models', {}).get(model_id, {}).get('versions', {}).keys())

    def get_latest_version(self, model_id: str) -> str:
        versions = self.list_versions(model_id)
        if not versions:
            raise ValueError(f"No versions available for model_id {model_id}")
        return max(versions, key=lambda v: parse.parse(v))

    def get_metadata(self):
        try:
            objects = self.client.list_objects()
            metadata = {"models": {}}

            for obj in objects:
                try:
                    content = self.client.cat(obj['Hash'])
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

    def store_metadata(self, metadata):
        try:
            new_cid = self.client.add_json(metadata)
            logging.info(f"Stored metadata with new CID: {new_cid}")
            return new_cid
        except Exception as e:
            logging.error(f"Error storing metadata: {str(e)}")
            raise

    def get_manifest_cid(self, model_id: str, version: str) -> str:
        metadata = self.get_metadata()
        if model_id not in metadata['models'] or version not in metadata['models'][model_id]['versions']:
            raise ValueError(f"No manifest CID found for {model_id} v{version}")
        return metadata['models'][model_id]['versions'][version]

    def get_all_latest_models(self):
        metadata = self.get_metadata()
        latest_models = {}
        for model_id, versions in metadata['models'].items():
            if versions:
                latest_version = versions['latest_version']
                latest_models[model_id] = {
                    'version': latest_version,
                    'cid': versions['versions'][latest_version]
                }
        return latest_models
    
    def get_all_objects(self) -> List[Dict]:
        objects = self.client.list_objects()
        all_objects = []
        for obj in objects:
            try:
                content = self.client.cat(obj['Hash'])
                data = json.loads(content) if content else {}
                all_objects.append({
                    'cid': obj['Hash'],
                    'content': data
                })
            except json.JSONDecodeError:
                all_objects.append({
                    'cid': obj['Hash'],
                    'content': 'Not a valid JSON'
                })
            except Exception as e:
                all_objects.append({
                    'cid': obj['Hash'],
                    'content': f'Error: {str(e)}'
                })
        return all_objects