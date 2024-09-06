import requests
import os
import logging

class IPFSClient:
    def __init__(self):
        ipfs_host = os.environ.get('IPFS_HOST', 'localhost')
        ipfs_port = os.environ.get('IPFS_PORT', '5001')
        self.base_url = f'http://{ipfs_host}:{ipfs_port}/api/v0'
        self.session = requests.Session()
        logging.info(f"IPFS Client initialized with base URL: {self.base_url}")

    def add_bytes(self, data):
        response = self.session.post(f'{self.base_url}/add', files={'file': ('filename', data)})
        response.raise_for_status()
        return response.json()['Hash']

    def add_stream(self, stream):
        response = self.session.post(f'{self.base_url}/add', files={'file': stream}, stream=True)
        response.raise_for_status()
        return response.json()['Hash']

    def cat(self, cid):
        response = self.session.post(f'{self.base_url}/cat', params={'arg': cid})
        response.raise_for_status()
        return response.content

    def cat_stream(self, cid):
        response = self.session.post(f'{self.base_url}/cat', params={'arg': cid}, stream=True)
        if response.status_code != 200:
            raise Exception(f"IPFS request failed: {response.status_code} {response.reason} - {response.text}")
        return response.iter_content(chunk_size=8192)

    def get_file_size(self, cid):
        response = self.session.post(f'{self.base_url}/files/stat', params={'arg': f'/ipfs/{cid}'})
        response.raise_for_status()
        return response.json()['Size']