import json
import requests
import os

class IPFSClient:
    def __init__(self):
        ipfs_host = os.environ.get('IPFS_HOST', 'ipfs')
        ipfs_port = os.environ.get('IPFS_PORT', '5001')
        self.base_url = f'http://{ipfs_host}:{ipfs_port}/api/v0'

    def cat(self, cid):
        params = {'arg': cid}
        response = requests.post(f'{self.base_url}/cat', params=params)
        return response.content

    def add_json(self, json_data):
        try:
            files = {'file': ('metadata.json', json.dumps(json_data))}
            response = requests.post(f'{self.base_url}/add', files=files)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error in add_json: {str(e)}")
            print(f"Response content: {e.response.content if e.response else 'No response content'}")
            print(f"Request payload: {json_data}")
            raise

    def get_json(self, cid):
        content = self.cat(cid)
        return json.loads(content)

    def add_bytes(self, data):
        files = {'file': ('filename', data)}
        response = requests.post(f'{self.base_url}/add', files=files)
        return response.json()

def ipfs_client():
    return IPFSClient()