import json
import requests
import os
import traceback

class IPFSClient:
    def __init__(self):
        ipfs_host = os.environ.get('IPFS_HOST', 'localhost')
        ipfs_port = os.environ.get('IPFS_PORT', '5001')
        self.base_url = f'http://{ipfs_host}:{ipfs_port}/api/v0'
        self.gateway_url = os.environ.get('IPFS_GATEWAY', 'https://ipfs.io').rstrip('/')
        self.session = requests.Session()
        print(f"Initialized IPFSClient with base_url: {self.base_url}, gateway_url: {self.gateway_url}")

    def cat(self, cid):
        print(f"Attempting to retrieve content for CID: {cid}")
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
            
            print(f"Successfully retrieved content for CID: {cid}, content length: {len(content)} bytes")
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
        print(f"Attempting to retrieve and parse JSON for CID: {cid}")
        try:
            content = self.cat(cid)
            json_data = json.loads(content)
            print(f"Successfully retrieved and parsed JSON for CID: {cid}")
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

    def list_objects(self):
        print("Attempting to list all pinned objects in IPFS")
        try:
            response = self.session.post(f'{self.base_url}/pin/ls')
            response.raise_for_status()
            result = response.json()
            
            objects = []
            for cid, info in result.get('Keys', {}).items():
                object_info = {'cid': cid, 'type': info.get('Type', 'Unknown')}
                try:
                    content = self.cat(cid)
                    try:
                        json_content = json.loads(content)
                        if isinstance(json_content, dict):
                            if 'model_id' in json_content:
                                object_info['category'] = 'Model Manifest'
                                object_info['model_id'] = json_content['model_id']
                                object_info['version'] = json_content.get('version', 'Unknown')
                            elif 'models' in json_content:
                                object_info['category'] = 'Model Index'
                            else:
                                object_info['category'] = 'JSON Data'
                            object_info['content'] = json_content
                        else:
                            object_info['category'] = 'JSON Data'
                            object_info['content'] = json_content
                    except json.JSONDecodeError:
                        object_info['category'] = 'Binary Data'
                        object_info['content'] = f"Binary data, size: {len(content)} bytes"
                except Exception as e:
                    object_info['category'] = 'Error'
                    object_info['content'] = f"Error retrieving content: {str(e)}"
                objects.append(object_info)
            
            print(f"Successfully listed {len(objects)} pinned objects from IPFS")
            for obj in objects:
                print(f"CID: {obj['cid']}, Type: {obj['type']}, Category: {obj['category']}, "
                      f"Model ID: {obj.get('model_id', 'N/A')}, Version: {obj.get('version', 'N/A')}")
            return objects
        except Exception as e:
            print(f"Error listing objects from IPFS: {str(e)}")
            print(traceback.format_exc())
            raise