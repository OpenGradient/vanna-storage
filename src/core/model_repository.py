import json
import logging
from uuid import UUID
from core.ipfs_client import IPFSClient
from core.model_version_metadata import ModelVersionMetadata
from packaging import version as version_parser
from datetime import datetime, timezone
from dataclasses import asdict
import hashlib
from typing import Any, List, Dict
import os
from werkzeug.wrappers.request import FileStorage
import time
import hashlib
import tempfile
import zipfile
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.datastructures import FileStorage
import tempfile
import os
from config.model_config import TEN_GB_IN_BYTES
from flask import abort
import zipfile

class ModelRepository :
    def __init__(self):
        self.client = IPFSClient()

    def upload_model(self, ipfs_uuid: UUID, new_files: Dict[str, FileStorage], existing_files: dict[str, str] | None, release_notes: str | None, is_major_version: bool | None) -> tuple:
        try:
            start_time = time.time()
            
            next_version = self._generate_next_version_number(ipfs_uuid, is_major_version)
            metadata_obj = ModelVersionMetadata(
                ipfs_uuid=str(ipfs_uuid),
                created_at=datetime.now(timezone.utc).isoformat(),
                version=next_version,
                release_notes=release_notes
            )
            total_size = 0

            # Handle existing files
            existing_files_time = time.time()
            if existing_files is not None and prev_version is not None and 'files' in prev_version:
                prev_version_files = prev_version['files']
                assert isinstance(prev_version_files, dict)
                for prev_filename, new_filename in existing_files.items():
                    if prev_filename in prev_version_files:
                        prev_file_metadata = prev_version_files[prev_filename]
                        assert isinstance(prev_file_metadata, dict)
                        prev_file_size = prev_file_metadata['file_size']
                        metadata_obj.add_file(
                            filename=new_filename,
                            file_cid=prev_file_metadata['file_cid'],
                            file_size=prev_file_size
                        )
                        total_size += int(prev_file_size)
            logging.info(f"Existing files processing time: {time.time() - existing_files_time:.2f} seconds")

            # Handle new files
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_file = {executor.submit(self.process_file, file_name, file_content, file_name.lower().endswith('.zip')): file_name for file_name, file_content in new_files.items()}
                for future in as_completed(future_to_file):
                    file_name = future_to_file[future]
                    try:
                        file_name, file_cid, file_size = future.result()
                        metadata_obj.add_file(file_name, file_cid, file_size)
                        total_size += file_size
                    except Exception as e:
                        logging.error(f"Error processing file {file_name}: {str(e)}")

            # Handle new files
            for file_name, file_content in new_files.items():
                logging.info(f"Processing file: {file_name}")
                
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    file_size = 0
                    checksum = hashlib.md5()
                    for chunk in file_content.stream:
                        temp_file.write(chunk)
                        checksum.update(chunk)
                        file_size += len(chunk)
                    temp_file.flush()

                    logging.info(f"File {file_name} processed. Size: {file_size} bytes")

                    # Check if the file is a zip
                    if file_name.lower().endswith('.zip'):
                        logging.info(f"Processing zip file: {file_name}")
                        with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                            for zip_info in zip_ref.infolist():
                                if not zip_info.is_dir():  # Skip directories
                                    with zip_ref.open(zip_info) as zip_file:
                                        zip_file_content = zip_file.read()
                                        zip_file_cid = self.client.add_bytes(zip_file_content)
                                        zip_file_path = zip_info.filename  # Preserve the original path
                                        metadata_obj.add_file(zip_file_path, zip_file_cid, zip_info.file_size)
                                        total_size += zip_info.file_size
                                        logging.info(f"Added file from zip: {zip_file_path}, CID: {zip_file_cid}, Size: {zip_info.file_size}")
                        logging.info(f"Zip file {file_name} extracted and added to IPFS")
                    else:
                        # Read the file content
                        with open(temp_file.name, 'rb') as f:
                            file_content = f.read()

                        # Verify checksum
                        if checksum.hexdigest() != hashlib.md5(file_content).hexdigest():
                            logging.error(f"Checksum mismatch for file {file_name}")
                            abort(500, description=f"File integrity check failed for {file_name}")

                        # Add the file to IPFS using add_bytes
                        file_cid = self.client.add_bytes(file_content)
                        logging.info(f"File {file_name} added to IPFS with CID: {file_cid}")

                        # Update metadata
                        metadata_obj.add_file(file_name, file_cid, file_size)
                        total_size += file_size

                # Clean up the temporary file
                os.unlink(temp_file.name)

            metadata_obj.total_size = total_size

            # Ensure all files have a created_at timestamp
            for file_info in metadata_obj.files.values():
                if 'created_at' not in file_info:
                    file_info['created_at'] = datetime.now(timezone.utc).isoformat()

            metadata_time = time.time()
            # Add debug logging
            logging.info(f"Metadata object before adding to IPFS: {metadata_obj}")
            logging.info(f"Total size: {total_size}")
            logging.info(f"Files in metadata: {metadata_obj.files}")

            manifest_cid = self.client.add_json(asdict(metadata_obj))
            logging.info(f"Metadata creation and IPFS addition time: {time.time() - metadata_time:.2f} seconds")
            
            total_time = time.time() - start_time
            logging.info(f"Total upload time: {total_time:.2f} seconds")
            logging.info(f"Manifest CID: {manifest_cid}")
            
            return manifest_cid, metadata_obj.version
        except Exception as e:
            logging.error(f"Error uploading model: {str(e)}")
            raise

    def process_file(self, file_name, file_content, is_zip):
        file_start_time = time.time()
        logging.info(f"Processing file: {file_name}")
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file_read_time = time.time()
            file_size = 0
            checksum = hashlib.md5()
            for chunk in file_content.stream:
                temp_file.write(chunk)
                checksum.update(chunk)
                file_size += len(chunk)
            temp_file.flush()
            logging.info(f"File read and checksum time: {time.time() - file_read_time:.2f} seconds")

            if is_zip:
                zip_time = time.time()
                for zip_file_name, zip_file_content, zip_file_size in self.process_zip_file(file_content):
                    zip_file_cid = self.client.add_file_stream(zip_file_content, zip_file_name)
                    metadata_obj.add_file(zip_file_name, zip_file_cid, zip_file_size)
                    total_size += zip_file_size
                logging.info(f"ZIP processing time: {time.time() - zip_time:.2f} seconds")
            else:
                non_zip_time = time.time()
                file_cid = self.client.add_file_stream(file_content.stream, file_name)
                logging.info(f"File {file_name} added to IPFS with CID: {file_cid}")
                logging.info(f"Non-ZIP processing time: {time.time() - non_zip_time:.2f} seconds")

        logging.info(f"Total file processing time: {time.time() - file_start_time:.2f} seconds")
        os.unlink(temp_file.name)

        return file_name, file_cid, file_size

    def process_zip_file(self, file_content):
        with zipfile.ZipFile(io.BytesIO(file_content.read()), 'r') as zip_ref:
            for zip_info in zip_ref.infolist():
                if not zip_info.is_dir():
                    with zip_ref.open(zip_info) as zip_file:
                        yield zip_info.filename, zip_file, zip_info.file_size

    def _generate_next_version_number(self, ipfs_uuid: UUID, is_major_version = False) -> str:
        versions = self.list_version_numbers(ipfs_uuid)
        if not versions:
            return f"{1}.{0:02d}"
        latest_version = max(versions, key=lambda v: [int(x) for x in v.split('.')])
        major, minor = map(int, latest_version.split('.'))
        minor += 1
        if minor > 99 or is_major_version:
            major += 1
            minor = 0
        return f"{major}.{minor:02d}"

    def download_model(self, ipfs_uuid: UUID, version: str) -> tuple[Dict[str, bytes], int]:
        try:
            manifest_cid = self.get_manifest_cid(ipfs_uuid, version)
            manifest: dict[str, Any] = self.client.get_json(manifest_cid)
            
            if not manifest or 'files' not in manifest:
                raise ValueError(f"Invalid manifest for {ipfs_uuid} v{version}")
            
            model_files = {}
            for file_name, file_info in manifest['files'].items():
                file_data = self.client.cat(file_info['file_cid'])
                if not file_data:
                    raise ValueError(f"Failed to retrieve file {file_name} for {ipfs_uuid} v{version}")
                model_files[file_name] = file_data
            
            return model_files, manifest.get('total_size', 0)
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

    def list_versions(self, ipfs_uuid: UUID) -> list[dict[str, Any]]:
        objects = self.client.list_objects()
        versions: list[dict[str, Any]] = []
        for obj in objects:
            try:
                content = obj.content
                if content and content.ipfs_uuid == ipfs_uuid:
                    versions.append(content.to_dict())
            except Exception as e:
                logging.error(f"Error processing object {obj.hash}: {str(e)}")
        return versions

    def list_version_numbers(self, ipfs_uuid: UUID) -> list[str]:
        versions = self.list_versions(ipfs_uuid)
        version_numbers: list[str] = []
        for version_metadata in versions:
            try:
                if 'version' in version_metadata:
                    version_numbers.append(version_metadata['version'])
            except Exception:
                logging.error(f"Error processing version {version_metadata}")

        return version_numbers

    def get_latest_version(self, ipfs_uuid: UUID) -> dict[str, Any] | None:
        versions = self.list_versions(ipfs_uuid)
        if not versions:
            return None

        max_version_number = version_parser.parse(versions[0]["version"])
        max_version = versions[0]

        # Find version with max_version_number
        for i in range(1, len(versions)):
            curr_version = versions[i]
            assert 'version' in curr_version, f"version field does not exist in {curr_version}"
            curr_version_number = curr_version['version']
            if version_parser.parse(curr_version_number) > max_version_number:
                max_version_number = version_parser.parse(curr_version_number)
                max_version = curr_version
        
        return max_version


    def get_latest_version_number(self, ipfs_uuid: UUID) -> str | None:
        latest_version = self.get_latest_version(ipfs_uuid)
        return latest_version["version"] if latest_version is not None else None

    def get_manifest_cid(self, ipfs_uuid: UUID, version: str) -> str:
        objects = self.client.list_objects()
        for obj in objects:
            try:
                content = self.client.cat(obj.hash)
                data = json.loads(content)
                if isinstance(data, dict) and data.get('ipfs_uuid') == ipfs_uuid and data.get('version') == version:
                    return obj.hash
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logging.error(f"Error processing object {obj.hash}: {str(e)}")
        raise ValueError(f"No manifest CID found for {ipfs_uuid} v{version}")

    def get_all_latest_models(self) -> dict[str, dict[str, str]]:
        objects = self.client.list_objects()
        latest_models: dict[str, dict[str, str]] = {}
        for obj in objects:
            try:
                content = self.client.cat(obj.hash)
                data = json.loads(content)
                if isinstance(data, dict) and 'ipfs_uuid' in data and 'version' in data:
                    ipfs_uuid = data['ipfs_uuid']
                    version = data['version']
                    created_at = data.get('created_at', '1970-01-01T00:00:00Z')  # Default to epoch if not present
                    if ipfs_uuid not in latest_models or version_parser.parse(version) > version_parser.parse(latest_models[ipfs_uuid]['version']):
                        latest_models[ipfs_uuid] = {
                            'version': version,
                            'cid': obj.hash,
                            'created_at': created_at
                        }
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logging.error(f"Error processing object {obj.hash}: {str(e)}")
        return latest_models
    
    def get_all_objects(self) -> List[Dict]:
        objects = self.client.list_objects()
        all_objects = []
        for obj in objects:
            try:
                content = self.client.cat(obj.hash)
                data = json.loads(content) if content else {}
                all_objects.append({
                    'cid': obj.hash,
                    'content': data
                })
            except json.JSONDecodeError:
                all_objects.append({
                    'cid': obj.hash,
                    'content': 'Not a valid JSON'
                })
            except Exception as e:
                all_objects.append({
                    'cid': obj.hash,
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
            updated_manifest = asdict(updated_metadata)
            new_manifest_cid = self.client.add_json(updated_manifest)
            
            return {'manifest_cid': new_manifest_cid, 'metadata': updated_manifest}
        except Exception as e:
            logging.error(f"Error in update_model_metadata: {str(e)}", exc_info=True)
            raise