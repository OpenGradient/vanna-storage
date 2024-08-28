import json
import requests
from typing import Any, Self
import os
import traceback
from dataclasses import asdict, dataclass
from flask import current_app

from core.model_version_metadata import ModelVersionMetadataFiles


@dataclass
class IPFSObject:
    hash: str
    type: Any
    content: ModelVersionMetadataFiles | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class IPFSClient:
    def __init__(self):
        ipfs_host = os.environ.get('IPFS_HOST', 'localhost')
        ipfs_port = os.environ.get('IPFS_PORT', '5001')
        self.base_url = f'http://{ipfs_host}:{ipfs_port}/api/v0'
        self.gateway_url = os.environ.get('IPFS_GATEWAY', 'https://ipfs.io').rstrip('/')
        self.session = requests.Session()
        print(f"Initialized IPFSClient with base_url: {self.base_url}, gateway_url: {self.gateway_url}")

    def cat(self, cid):
        # print(f"Attempting to retrieve content for CID: {cid}")
        try:
            if isinstance(cid, dict):
                if 'Hash' in cid:
                    cid = cid['Hash']
                elif 'Ref' in cid:
                    cid = cid['Ref']
                else:
                    raise ValueError(f"Invalid CID format: {cid}")
            
            # Use the local IPFS node for retrieval
            response = self.session.post(f'{self.base_url}/cat', params={'arg': cid})
            response.raise_for_status()
            content = response.content
            
            # print(f"Successfully retrieved content for CID: {cid}, content length: {len(content)} bytes")
            return content
        except requests.exceptions.RequestException as e:
            print(f"Error in cat for CID {cid}: {str(e)}")
            print(traceback.format_exc())
            raise

    def add_json(self, json_data):
        print("Attempting to add JSON to IPFS")
        try:
            response = self.session.post(
                f"{self.base_url}/add",
                files={'file': ('filename', json.dumps(json_data))}
            )
            response.raise_for_status()
            result = response.json()
            cid = result['Hash']
            print(f"Successfully added JSON to IPFS with CID: {cid}")
            return cid
        except Exception as e:
            print(f"Error in add_json: {str(e)}")
            print(traceback.format_exc())
            raise

    def get_json(self, cid):
        # print(f"Attempting to retrieve and parse JSON for CID: {cid}")
        try:
            content = self.cat(cid)
            json_data = json.loads(content)
            # print(f"Successfully retrieved and parsed JSON for CID: {cid}")
            return json_data
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for CID {cid}: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error in get_json for CID {cid}: {str(e)}")
            raise

    def add_bytes(self, data):
        print(f"Attempting to add bytes to IPFS, data length: {len(data)} bytes")
        try:
            response = self.session.post(f'{self.base_url}/add', files={'file': ('filename', data)})
            response.raise_for_status()
            result = response.json()
            cid = result['Hash']
            print(f"Successfully added bytes to IPFS with CID: {cid}")
            return cid
        except Exception as e:
            print(f"Error in add_bytes: {str(e)}")
            print(traceback.format_exc())
            raise

    def list_objects(self) -> list[IPFSObject]:
        try:
            response = self.session.post(f'{self.base_url}/pin/ls')
            response.raise_for_status()
            result = response.json()
            
            objects: list[IPFSObject] = []
            for cid, info in result.get('Keys', {}).items():
                object_info = IPFSObject(hash=cid, type=info.get('Type'))
                try:
                    content = self.cat(cid)
                    json_content: dict[str, Any] = json.loads(content)
                    object_info.content = ModelVersionMetadataFiles(
                        ipfs_uuid=json_content.get('ipfs_uuid'),
                        version=json_content.get('version'),
                        release_notes=json_content.get('release_notes'),
                        files=json_content.get('files'),
                        created_at=json_content.get('created_at'),
                    )
                except json.JSONDecodeError:
                    current_app.logger.warn(f"invalid JSON from content with hash: {cid}")
                    continue
                except UnicodeDecodeError as e:
                    current_app.logger.warn(f"UnicodeDecodeError for cid: {cid} |\n{str(e)}")
                    continue
                except Exception as e:
                    current_app.logger.exception(f"Exception for cid: {cid} |\n{str(e)}")
                    continue
                objects.append(object_info)

            return objects
        except Exception as e:
            print(f"Error listing objects from IPFS: {str(e)}")
            print(traceback.format_exc())
            raise