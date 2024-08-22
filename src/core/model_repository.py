import json
import logging
from uuid import UUID
from core.ipfs_client import IPFSClient
from core.model_version_metadata import ModelVersionMetadata
from packaging import version as parse
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional
import os

class ModelRepository:
    def __init__(self):
        self.client = IPFSClient()

    def upload_model(self, ipfs_uuid: UUID, files: Dict[str, Any], metadata: dict) -> tuple:
        try:
            major_version, minor_version = self._generate_new_version(ipfs_uuid)
            
            metadata_obj = ModelVersionMetadata(
                ipfs_uuid=ipfs_uuid,
                created_at=datetime.now(timezone.utc).isoformat(),
                major_version=major_version,
                minor_version=minor_version,
                release_notes=metadata.get('release_notes')
            )
            
            for key, value in metadata.items():
                setattr(metadata_obj, key, value)
            
            for file_name, file_content in files.items():
                file_type = os.path.splitext(file_name)[1][1:].lower()
                file_cid = self.client.add_bytes(file_content.read())
                metadata_obj.add_file(file_name, file_type, file_cid)
            
            # Ensure all files have a created_at timestamp
            for file_info in metadata_obj.files.values():
                if 'created_at' not in file_info:
                    file_info['created_at'] = datetime.now(timezone.utc).isoformat()
            
            manifest_cid = self.client.add_json(metadata_obj.to_dict())
            
            logging.info(f"Uploaded model {ipfs_uuid} version {metadata_obj.version} with manifest CID: {manifest_cid}")
            return manifest_cid, metadata_obj.version
        except Exception as e:
            logging.error(f"Error uploading model: {str(e)}")
            raise

    def _generate_new_version(self, ipfs_uuid: UUID) -> tuple:
        versions = self.list_versions(ipfs_uuid)
        if not versions:
            return 1, 0
        latest_version = max(versions, key=lambda v: [int(x) for x in v.split('.')])
        major, minor = map(int, latest_version.split('.'))
        minor += 1
        if minor > 99:
            major += 1
            minor = 0
        return major, minor

    def download_model(self, ipfs_uuid: UUID, version: str) -> Dict[str, bytes]:
        try:
            manifest_cid = self.get_manifest_cid(ipfs_uuid, version)
            manifest = self.client.get_json(manifest_cid)
            
            if not manifest or 'files' not in manifest:
                raise ValueError(f"Invalid manifest for {ipfs_uuid} v{version}")
            
            model_files = {}
            for file_name, file_info in manifest['files'].items():
                file_data = self.client.cat(file_info['file_cid'])
                if not file_data:
                    raise ValueError(f"Failed to retrieve file {file_name} for {ipfs_uuid} v{version}")
                model_files[file_name] = file_data
            
            return model_files
        except Exception as e:
            logging.error(f"Error in download_model: {str(e)}", exc_info=True)
            raise

    def get_model_info(self, ipfs_uuid: UUID, version: str) -> Dict:
        try:
            manifest_cid = self.get_manifest_cid(ipfs_uuid, version)
            manifest = self.client.get_json(manifest_cid)
            
            if not manifest:
                raise ValueError(f"Empty manifest for {ipfs_uuid} v{version}")
            
            return manifest
        except Exception as e:
            logging.error(f"Error in get_model_info: {str(e)}", exc_info=True)
            raise

    def list_versions(self, ipfs_uuid: UUID) -> List[str]:
        objects = self.client.list_objects()
        versions = []
        for obj in objects:
            try:
                content = self.client.cat(obj['Hash'])
                data = json.loads(content)
                if isinstance(data, dict) and data.get('ipfs_uuid') == ipfs_uuid and 'version' in data:
                    versions.append(data['version'])
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logging.error(f"Error processing object {obj['Hash']}: {str(e)}")
        return versions

    def get_latest_version(self, ipfs_uuid: UUID) -> str:
        versions = self.list_versions(ipfs_uuid)
        if not versions:
            raise ValueError(f"No versions available for ipfs_uuid {ipfs_uuid}")
        return max(versions, key=lambda v: parse.parse(v))

    def get_manifest_cid(self, ipfs_uuid: UUID, version: str) -> str:
        objects = self.client.list_objects()
        for obj in objects:
            try:
                content = self.client.cat(obj['Hash'])
                data = json.loads(content)
                if isinstance(data, dict) and data.get('ipfs_uuid') == ipfs_uuid and data.get('version') == version:
                    return obj['Hash']
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logging.error(f"Error processing object {obj['Hash']}: {str(e)}")
        raise ValueError(f"No manifest CID found for {ipfs_uuid} v{version}")

    def get_all_latest_models(self) -> Dict[str, Dict[str, str]]:
        objects = self.client.list_objects()
        latest_models = {}
        for obj in objects:
            try:
                content = self.client.cat(obj['Hash'])
                data = json.loads(content)
                if isinstance(data, dict) and 'ipfs_uuid' in data and 'version' in data:
                    ipfs_uuid = data['ipfs_uuid']
                    version = data['version']
                    created_at = data.get('created_at', '1970-01-01T00:00:00Z')  # Default to epoch if not present
                    if ipfs_uuid not in latest_models or parse.parse(version) > parse.parse(latest_models[ipfs_uuid]['version']):
                        latest_models[ipfs_uuid] = {
                            'version': version,
                            'cid': obj['Hash'],
                            'created_at': created_at
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

    def update_model_metadata(self, ipfs_uuid: UUID, version: str, new_metadata: dict) -> dict:
        try:
            manifest_cid = self.get_manifest_cid(ipfs_uuid, version)
            manifest = self.client.get_json(manifest_cid)
            
            if not manifest:
                raise ValueError(f"Invalid manifest for {ipfs_uuid} v{version}")
            
            # Update the manifest with new metadata
            for key, value in new_metadata.items():
                if value is None:
                    manifest.pop(key, None)
                else:
                    manifest[key] = value
            
            # Create a new ModelVersionMetadata object with updated information
            updated_metadata = ModelVersionMetadata.from_dict(manifest)
            
            # Convert back to dict and add to IPFS
            updated_manifest = updated_metadata.to_dict()
            new_manifest_cid = self.client.add_json(updated_manifest)
            
            return {'manifest_cid': new_manifest_cid, 'metadata': updated_manifest}
        except Exception as e:
            logging.error(f"Error in update_model_metadata: {str(e)}", exc_info=True)
            raise