import json
import logging
from core.ipfs_client import IPFSClient
from core.model_metadata import ModelMetadata
from packaging import version as parse
from datetime import datetime
from typing import List, Dict
import os
from werkzeug.utils import secure_filename

class ModelRepository:
    def __init__(self):
        self.client = IPFSClient()

    def upload_model(self, model_id: str, file, metadata: dict) -> tuple:
        try:
            file_name = secure_filename(file.filename)
            file_type = os.path.splitext(file_name)[1][1:].lower()
            
            serialized_model = file.read()
            model_file_cid = self.client.add_bytes(serialized_model)
            
            major_version, minor_version = self._generate_new_version(model_id)
            
            metadata_obj = ModelMetadata(
                model_id=model_id,
                file_name=file_name,
                file_type=file_type,
                file_cid=model_file_cid,
                created_at=datetime.now().isoformat(),
                major_version=major_version,
                minor_version=minor_version,
                **metadata
            )
            
            manifest_cid = self.client.add_json(metadata_obj.to_dict())
            
            logging.debug(f"Uploaded model {model_id} version {metadata_obj.version} with manifest CID: {manifest_cid}")
            return manifest_cid, metadata_obj.version
        except Exception as e:
            logging.error(f"Error uploading model: {str(e)}")
            raise

    def _generate_new_version(self, model_id: str) -> tuple:
        versions = self.list_versions(model_id)
        if not versions:
            return 1, 0
        latest_version = max(versions, key=lambda v: [int(x) for x in v.split('.')])
        major, minor = map(int, latest_version.split('.'))
        minor += 1
        if minor > 99:
            major += 1
            minor = 0
        return major, minor

    def download_model(self, model_id: str, version: str) -> bytes:
        try:
            manifest_cid = self.get_manifest_cid(model_id, version)
            manifest = self.client.get_json(manifest_cid)
            
            if not manifest or 'file_cid' not in manifest:
                raise ValueError(f"Invalid manifest for {model_id} v{version}")
            
            model_data = self.client.cat(manifest['file_cid'])
            if not model_data:
                raise ValueError(f"Failed to retrieve model data for {model_id} v{version}")
            
            return model_data
        except Exception as e:
            logging.error(f"Error in download_model: {str(e)}", exc_info=True)
            raise

    def get_model_info(self, model_id: str, version: str) -> Dict:
        try:
            manifest_cid = self.get_manifest_cid(model_id, version)
            manifest = self.client.get_json(manifest_cid)
            
            if not manifest:
                raise ValueError(f"Empty manifest for {model_id} v{version}")
            
            return manifest
        except Exception as e:
            logging.error(f"Error in get_model_info: {str(e)}", exc_info=True)
            raise

    def list_versions(self, model_id: str) -> List[str]:
        objects = self.client.list_objects()
        versions = []
        for obj in objects:
            try:
                content = self.client.cat(obj['Hash'])
                data = json.loads(content)
                if isinstance(data, dict) and data.get('model_id') == model_id and 'version' in data:
                    versions.append(data['version'])
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logging.error(f"Error processing object {obj['Hash']}: {str(e)}")
        return versions

    def get_latest_version(self, model_id: str) -> str:
        versions = self.list_versions(model_id)
        if not versions:
            raise ValueError(f"No versions available for model_id {model_id}")
        return max(versions, key=lambda v: parse.parse(v))

    def get_manifest_cid(self, model_id: str, version: str) -> str:
        objects = self.client.list_objects()
        for obj in objects:
            try:
                content = self.client.cat(obj['Hash'])
                data = json.loads(content)
                if isinstance(data, dict) and data.get('model_id') == model_id and data.get('version') == version:
                    return obj['Hash']
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logging.error(f"Error processing object {obj['Hash']}: {str(e)}")
        raise ValueError(f"No manifest CID found for {model_id} v{version}")

    def get_all_latest_models(self) -> Dict[str, Dict[str, str]]:
        objects = self.client.list_objects()
        latest_models = {}
        for obj in objects:
            try:
                content = self.client.cat(obj['Hash'])
                data = json.loads(content)
                if isinstance(data, dict) and 'model_id' in data and 'version' in data:
                    model_id = data['model_id']
                    version = data['version']
                    if model_id not in latest_models or parse.parse(version) > parse.parse(latest_models[model_id]['version']):
                        latest_models[model_id] = {
                            'version': version,
                            'cid': obj['Hash']
                        }
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logging.error(f"Error processing object {obj['Hash']}: {str(e)}")
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

    def update_model_metadata(self, model_id: str, version: str, new_metadata: dict) -> dict:
        try:
            manifest_cid = self.get_manifest_cid(model_id, version)
            manifest = self.client.get_json(manifest_cid)
            
            if not manifest:
                raise ValueError(f"Invalid manifest for {model_id} v{version}")
            
            # Update the manifest with new metadata
            for key, value in new_metadata.items():
                if value is None:
                    manifest.pop(key, None)
                else:
                    manifest[key] = value
            
            # Create a new ModelMetadata object with updated information
            updated_metadata = ModelMetadata.from_dict(manifest)
            
            # Convert back to dict and add to IPFS
            updated_manifest = updated_metadata.to_dict()
            new_manifest_cid = self.client.add_json(updated_manifest)
            
            return {'manifest_cid': new_manifest_cid, 'metadata': updated_manifest}
        except Exception as e:
            logging.error(f"Error in update_model_metadata: {str(e)}", exc_info=True)
            raise