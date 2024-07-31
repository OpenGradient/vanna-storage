import json
import requests
import os
import traceback

class IPFSClient:
    def __init__(self):
        ipfs_host = os.environ.get('IPFS_HOST', 'ipfs')
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
        print("Attempting to list all objects in IPFS")
        try:
            response = self.session.post(f'{self.base_url}/pin/ls')
            response.raise_for_status()
            print(f"Raw response from IPFS: {response.text}")
            
            objects = []
            for line in response.iter_lines():
                if line:
                    print(f"Processing line: {line}")
                    try:
                        decoded_line = line.decode('utf-8')
                        print(f"Decoded line: {decoded_line}")
                        obj = json.loads(decoded_line)
                        if isinstance(obj, dict) and 'Keys' in obj:
                            for key, value in obj['Keys'].items():
                                objects.append({'Hash': key, 'Type': value.get('Type', 'Unknown')})
                                print(f"Added object with Hash: {key}, Type: {value.get('Type', 'Unknown')}")
                        elif 'Ref' in obj:
                            objects.append({'Hash': obj['Ref']})
                            print(f"Added object with Ref: {obj['Ref']}")
                        else:
                            objects.append({'Hash': decoded_line.strip()})
                            print(f"Added object with Hash: {decoded_line.strip()}")
                    except UnicodeDecodeError:
                        hex_line = line.hex()
                        print(f"Failed to decode, using hex: {hex_line}")
                        objects.append({'Hash': hex_line})
                    except json.JSONDecodeError:
                        fallback_line = line.decode('utf-8', errors='replace').strip()
                        print(f"Failed to parse JSON, using fallback: {fallback_line}")
                        objects.append({'Hash': fallback_line})
            
            print(f"Successfully listed {len(objects)} objects from IPFS")
            print(f"Objects: {objects}")
            return objects
        except Exception as e:
            print(f"Error listing objects from IPFS: {str(e)}")
            print(traceback.format_exc())
            raise
